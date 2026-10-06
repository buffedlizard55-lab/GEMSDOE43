#!/usr/bin/env python3
"""Round-2 spatial holdout: MCLP placement (Arms A/B) and MG01 geology (Arm C).

Frozen protocol (registry/experiment_g43_mclp.json): same four-colour 20-km blocks,
3-px held-edge guard, 2-px training-trace guard, equal 40,000-px mass, and official
300-m triangular DTI without the known-mask as round 1. The recomputed H42 reference
must match the round-1 receipt within 1e-6 or the run aborts.

Debug flags (--folds/--budget/--candidate-cap/--out) exist only for smoke tests;
the scored run uses the frozen defaults and writes evidence/holdout_g43_mclp.json.
"""
from __future__ import annotations

import argparse
import gc
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe43.density import geometric_mean, greedy_pack  # noqa: E402
from gemsdoe43.h42 import build_h42_surfaces  # noqa: E402
from gemsdoe43.io import read_labels_and_footprint  # noqa: E402
from gemsdoe43.mclp import lazy_greedy_cover  # noqa: E402
from gemsdoe43.metric import dti  # noqa: E402
from gemsdoe43.sup01 import load_feature_stack, train_predict_proba  # noqa: E402
from gemsdoe43.surfaces import build_mg01_surface  # noqa: E402

F32 = np.float32
FOLD_PIXELS = 200
EDGE_GUARD_PX = 3.0
TRAINING_TRACE_GUARD_PX = 2.0
H42_CAP = 2_000_000
REF_NAME = "REF_SH_basin_strong|sep4.0|N40000"
ROUND1_RECEIPT = "evidence/holdout_g43_cg01.json"
ROUND1_REF_ARM = "SH_basin_strong|sep4.0|N40000"


def four_colour_fold_ids(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    row_blocks = np.arange(height, dtype=np.int32) // FOLD_PIXELS
    col_blocks = np.arange(width, dtype=np.int32) // FOLD_PIXELS
    return (row_blocks[:, None] + 2 * col_blocks[None, :]) % 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--folds", type=int, nargs="*", default=[0, 1, 2, 3])
    parser.add_argument("--budget", type=int, default=40_000)
    parser.add_argument("--candidate-cap", type=int, default=300_000)
    parser.add_argument("--out", type=Path, default=ROOT / "evidence/holdout_g43_mclp.json")
    args = parser.parse_args()
    root = args.root.resolve()
    budget = args.budget
    candidate_cap = args.candidate_cap
    frozen_run = (
        sorted(args.folds) == [0, 1, 2, 3]
        and budget == 40_000
        and candidate_cap == 300_000
    )
    started = time.time()

    labels, footprint, _ = read_labels_and_footprint(root)
    fold_id = four_colour_fold_ids(labels.shape)
    round1 = json.loads((root / ROUND1_RECEIPT).read_text(encoding="utf-8"))
    round1_ref = round1["summary"][ROUND1_REF_ARM]
    round1_folds = {f["fold"]: f["arms"][ROUND1_REF_ARM]["dti"] for f in round1["folds"]}

    print("Building H42 SH surface...", flush=True)
    surfaces = build_h42_surfaces(root)
    sh_surface = surfaces["SH_basin_strong"]
    del surfaces
    print("Building MG01 surface...", flush=True)
    mg_score, mg_valid = build_mg01_surface(root)
    print(f"MG01 valid cells on footprint: {int(np.count_nonzero(mg_valid & footprint)):,}",
          flush=True)
    ens_surface = geometric_mean(
        {"sh": sh_surface, "mg": mg_score}, {"sh": 0.5, "mg": 0.5})
    ens_surface[~mg_valid] = 0.0
    print("Loading SUP01 feature stack (19 bands + scarp + flag)...", flush=True)
    feature_stack, bands_valid, feature_names = load_feature_stack(root)
    print(f"SUP01 stack: {feature_stack.shape}, "
          f"bands-valid on footprint: {int(np.count_nonzero(bands_valid & footprint)):,}",
          flush=True)

    folds: list[dict] = []
    arm_dti: dict[str, list[float]] = {}
    for fold_number in args.folds:
        fold_start = time.time()
        held = (fold_id == fold_number) & footprint
        forbidden = distance_transform_edt(~held) <= EDGE_GUARD_PX
        train_region = footprint & ~forbidden
        training = labels & ~forbidden
        evaluation = held & (distance_transform_edt(held) > EDGE_GUARD_PX)
        training_distance = distance_transform_edt(~training).astype(F32)
        allowed = evaluation & (training_distance > TRAINING_TRACE_GUARD_PX)
        eval_truth = evaluation & labels
        truth_distance = distance_transform_edt(~eval_truth)
        arms: dict[str, dict] = {}

        def score_arm(name: str, selected: np.ndarray, note: str = "",
                      extra: dict | None = None) -> None:
            result = dti(selected.astype(F32), labels, footprint=evaluation,
                         truth_distance=truth_distance)
            entry = {
                "n_px": int(selected.sum()),
                "mass": float(selected.sum(dtype=np.float64)),
                "tp": round(float(result["tp"]), 2),
                "fp": round(float(result["fp"]), 2),
                "fn": round(float(result["fn"]), 2),
                "dti": round(float(result["dti"]), 6),
                "credit_per_mass": round(float(result["credit_per_mass"]), 5),
                "note": note,
            }
            if extra:
                entry.update(extra)
            arms[name] = entry
            arm_dti.setdefault(name, []).append(entry["dti"])

        # REF: protocol-drift guard, identical call as round 1.
        ref_selected = greedy_pack(sh_surface, allowed, min_sep=4.0, budget=budget,
                                   candidate_cap=H42_CAP)
        score_arm(REF_NAME, ref_selected, "recomputed H42 reference; drift guard")
        del ref_selected

        # Arm A: H42-SH surface + MCLP.
        demand_a = np.where(evaluation, sh_surface.astype(np.float64), 0.0)
        t0 = time.time()
        sel_a, stats_a = lazy_greedy_cover(demand_a, allowed, budget=budget,
                                           candidate_cap=candidate_cap)
        t_a = time.time() - t0
        if int(sel_a.sum()) != min(budget, int(allowed.sum())):
            raise AssertionError("Arm A did not satisfy the emission budget")
        score_arm("A_SH_MCLP|N40000", sel_a, "H42-SH surface + MCLP lazy greedy",
                  extra={"mclp_objective": round(stats_a["objective"], 3),
                         "mclp_recomputes": stats_a["recomputes"],
                         "mclp_candidates": stats_a["candidates"],
                         "mclp_seconds": round(t_a, 1)})
        del demand_a, sel_a, stats_a
        gc.collect()

        # Arm B: MG01 surface + MCLP.
        mg_allowed = allowed & mg_valid
        demand_b = np.where(evaluation & mg_valid, mg_score.astype(np.float64), 0.0)
        t0 = time.time()
        sel_b, stats_b = lazy_greedy_cover(demand_b, mg_allowed, budget=budget,
                                           candidate_cap=candidate_cap)
        t_b = time.time() - t0
        if int(sel_b.sum()) != min(budget, int(mg_allowed.sum())):
            raise AssertionError("Arm B did not satisfy the emission budget")
        score_arm("B_MG01_MCLP|N40000", sel_b, "MG01 surface + MCLP lazy greedy",
                  extra={"mclp_objective": round(stats_b["objective"], 3),
                         "mclp_recomputes": stats_b["recomputes"],
                         "mclp_candidates": stats_b["candidates"],
                         "mclp_seconds": round(t_b, 1)})
        del demand_b, sel_b, stats_b
        gc.collect()

        # Arm C: MG01 surface + fixed sep-4.0 packing (geology isolation control).
        sel_c = greedy_pack(mg_score, mg_allowed, min_sep=4.0, budget=budget,
                            candidate_cap=H42_CAP)
        score_arm("C_MG01_sep4.0|N40000", sel_c,
                  "MG01 surface + fixed sep-4.0 packing (control)")
        del sel_c

        # Arm E: SH/MG01 50-50 ensemble + fixed sep-4.0 packing (round-2b backup).
        ens_allowed = allowed & mg_valid
        sel_e = greedy_pack(ens_surface, ens_allowed, min_sep=4.0, budget=budget,
                            candidate_cap=H42_CAP)
        score_arm("E_ENS_SH_MG01|sep4.0|N40000", sel_e,
                  "50/50 SH/MG01 geometric-mean ensemble + sep-4.0 (round-2b)")
        del sel_e

        # Arm D: SUP01 supervised ranker + fixed sep-4.0 packing (round-2b backup).
        sup_allowed = allowed & bands_valid
        train_cells = np.flatnonzero((train_region & bands_valid).ravel())
        pred_cells = np.flatnonzero(sup_allowed.ravel())
        train_labels = labels.ravel()[train_cells]
        t0 = time.time()
        proba, sup_info = train_predict_proba(
            feature_stack, train_cells, train_labels, pred_cells)
        t_train = time.time() - t0
        proba_grid = np.zeros(labels.shape, dtype=F32)
        proba_grid.ravel()[pred_cells] = proba
        del proba
        sel_d = greedy_pack(proba_grid, sup_allowed, min_sep=4.0, budget=budget,
                            candidate_cap=H42_CAP)
        if int(sel_d.sum()) != min(budget, int(sup_allowed.sum())):
            raise AssertionError("Arm D did not satisfy the emission budget")
        score_arm("D_SUP01_HGB|sep4.0|N40000", sel_d,
                  "SUP01 HGB ranker + sep-4.0 packing (round-2b)",
                  extra={"sup_n_train": sup_info["n_train"],
                         "sup_n_train_positive": sup_info["n_train_positive"],
                         "sup_n_iter": sup_info["n_iter"],
                         "sup_train_seconds": round(t_train, 1)})
        del sel_d, proba_grid, train_cells, pred_cells, train_labels

        fold = {
            "fold": fold_number,
            "evaluation_cells": int(evaluation.sum()),
            "evaluation_truth_pixels": int(eval_truth.sum()),
            "eligible_emission_cells": int(allowed.sum()),
            "mg01_valid_eligible_cells": int(np.count_nonzero(mg_allowed)),
            "arms": arms,
            "seconds": round(time.time() - fold_start, 1),
        }
        folds.append(fold)
        print(f"fold {fold_number}: " + ", ".join(
            f"{name}={arms[name]['dti']:.6f}" for name in
            [REF_NAME, "A_SH_MCLP|N40000", "B_MG01_MCLP|N40000", "C_MG01_sep4.0|N40000",
             "E_ENS_SH_MG01|sep4.0|N40000", "D_SUP01_HGB|sep4.0|N40000"]
        ) + f" elapsed={fold['seconds']:.1f}s", flush=True)
        del held, forbidden, train_region, training, evaluation, eval_truth
        del training_distance, truth_distance, allowed, mg_allowed
        gc.collect()

    summary = {
        name: {
            "mean_dti": round(float(np.mean(scores)), 6),
            "min_dti": round(float(np.min(scores)), 6),
            "max_dti": round(float(np.max(scores)), 6),
            "folds": len(scores),
        }
        for name, scores in sorted(arm_dti.items())
    }

    # Protocol-drift guard against the frozen round-1 receipt.
    drift_mismatches = []
    if REF_NAME in summary and frozen_run:
        for key in ("mean_dti", "min_dti", "max_dti"):
            if abs(summary[REF_NAME][key] - round1_ref[key]) > 1e-6:
                drift_mismatches.append(
                    {"summary_field": key, "local": summary[REF_NAME][key],
                     "round1": round1_ref[key]})
        for fold in folds:
            delta = abs(fold["arms"][REF_NAME]["dti"] - round1_folds[fold["fold"]])
            if delta > 1e-6:
                drift_mismatches.append(
                    {"fold": fold["fold"], "absolute_dti_delta": delta})
    drift_status = "NOT_CHECKED" if not frozen_run else (
        "PASS" if not drift_mismatches else "FAIL")

    gate = {}
    ref_mean = summary.get(REF_NAME, {}).get("mean_dti")
    for arm in ("A_SH_MCLP|N40000", "B_MG01_MCLP|N40000", "C_MG01_sep4.0|N40000"):
        if arm not in summary or ref_mean is None:
            gate[arm] = {"status": "NOT_RUN"}
            continue
        wins = sum(
            fold["arms"][arm]["dti"] > fold["arms"][REF_NAME]["dti"] for fold in folds
        )
        beats = summary[arm]["mean_dti"] > ref_mean
        gate[arm] = {
            "gate_definition": "preregistered: 4-fold mean strictly greater + >=3/4 wins",
            "candidate_mean_dti": summary[arm]["mean_dti"],
            "reference_mean_dti": ref_mean,
            "candidate_mean_beats_reference": bool(beats),
            "fold_wins_vs_reference": int(wins),
            "minimum_fold_wins_required": 3,
            "passes_holdout_promotion_gate": bool(
                frozen_run and drift_status == "PASS" and beats and wins >= 3),
        }
    # Corrected gate for round-2b arms (fold 0 selected them): folds 1-3 only.
    clean_folds = [fold for fold in folds if fold["fold"] in (1, 2, 3)]
    for arm in ("D_SUP01_HGB|sep4.0|N40000", "E_ENS_SH_MG01|sep4.0|N40000"):
        if arm not in summary or ref_mean is None or len(clean_folds) != 3:
            gate[arm] = {"status": "NOT_RUN_OR_NO_CLEAN_FOLDS"}
            continue
        arm_mean_13 = float(np.mean([fold["arms"][arm]["dti"] for fold in clean_folds]))
        ref_mean_13 = float(np.mean([fold["arms"][REF_NAME]["dti"] for fold in clean_folds]))
        wins_13 = sum(fold["arms"][arm]["dti"] > fold["arms"][REF_NAME]["dti"]
                      for fold in clean_folds)
        gate[arm] = {
            "gate_definition": "corrected round-2b: folds 1-3 mean strictly greater + 3/3 wins (fold 0 excluded as selection fold)",
            "candidate_mean_folds1_3": round(arm_mean_13, 6),
            "reference_mean_folds1_3": round(ref_mean_13, 6),
            "candidate_mean_beats_reference": bool(arm_mean_13 > ref_mean_13),
            "fold_wins_folds1_3": int(wins_13),
            "minimum_fold_wins_required": 3,
            "candidate_mean_4fold": summary[arm]["mean_dti"],
            "passes_holdout_promotion_gate": bool(
                frozen_run and drift_status == "PASS"
                and arm_mean_13 > ref_mean_13 and wins_13 >= 3),
        }

    passing = [arm for arm, result in gate.items()
               if result.get("passes_holdout_promotion_gate")]
    if passing:
        best = max(passing, key=lambda arm: summary[arm]["mean_dti"])
        # Tie-break within 1e-6 prefers the newest geology: D > E > B > A.
        novelty = {"D_SUP01_HGB|sep4.0|N40000": 4, "E_ENS_SH_MG01|sep4.0|N40000": 3,
                   "B_MG01_MCLP|N40000": 2, "A_SH_MCLP|N40000": 1,
                   "C_MG01_sep4.0|N40000": 0}
        for arm in passing:
            if (abs(summary[arm]["mean_dti"] - summary[best]["mean_dti"]) <= 1e-6
                    and novelty.get(arm, -1) > novelty.get(best, -1)):
                best = arm
    else:
        best = None

    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {"python": platform.python_version(), "numpy": np.__version__},
        "frozen_run": frozen_run,
        "params": {"budget": budget, "candidate_cap": candidate_cap,
                   "folds": sorted(args.folds)},
        "design": {
            "folds": 4, "fold_cells": FOLD_PIXELS,
            "fold_formula": "(row//200 + 2*(col//200)) % 4",
            "outer_guard_px": EDGE_GUARD_PX,
            "training_catalogue_guard_px": TRAINING_TRACE_GUARD_PX,
            "equal_mass_comparison": f"all arms scored at N={budget}",
            "truth_scope": "withheld pixels from the published catalogue; not hidden competition truth",
            "known_catalogue_mask": "not passed to the metric: held-out catalogue positives are the truth",
        },
        "reference_drift_guard": {
            "status": drift_status,
            "round1_receipt": ROUND1_RECEIPT,
            "round1_reference_mean_dti": round1_ref["mean_dti"],
            "local_reference_mean_dti": summary.get(REF_NAME, {}).get("mean_dti"),
            "mismatches": drift_mismatches,
        },
        "sup01_features": feature_names,
        "summary": summary,
        "gate": gate,
        "passing_arms": passing,
        "primary_arm": best,
        "folds": folds,
        "interpretation_limit": (
            "This holdout tests recovery of spatially withheld published faults only. "
            "It is not an estimate or guarantee of public-board, private Phase 1, or final Phase 2 score."
        ),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    out = args.out if args.out.is_absolute() else root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("\nRound-2 summary:")
    for name, stat in summary.items():
        print(f"  {name:28s} mean={stat['mean_dti']:.6f} min={stat['min_dti']:.6f} "
              f"max={stat['max_dti']:.6f}")
    print(f"Drift guard: {drift_status}; gate: {json.dumps(gate, indent=2)}")
    try:
        receipt_label = str(out.relative_to(root))
    except ValueError:
        receipt_label = str(out)
    print(f"Primary arm: {best}; receipt: {receipt_label}")
    if frozen_run and drift_status == "FAIL":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
