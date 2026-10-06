#!/usr/bin/env python3
"""Reproduce GEMSDOE41 H42 spatial validation and evaluate preregistered G43-CG01.

No public leaderboard is read. This is a spatially blocked catalogue-recovery
instrument, not a forecast of the hidden competition score. By design the same four
folds, edge guard, training-trace thinning, H42 surfaces, separation, budgets and
metric are used as the public H42 report so its scalar can be independently checked.
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe43.cg01 import build_candidate_score
from gemsdoe43.density import greedy_pack
from gemsdoe43.h42 import build_h42_surfaces
from gemsdoe43.io import read_labels_and_footprint
from gemsdoe43.metric import dti

F32 = np.float32
SEPARATIONS = (3.0, 4.0)
BUDGETS = (10_000, 20_000, 40_000)
H42_SURFACES = ("SA_slope_scarp", "SB_slope_scarp_tmi", "SH_basin_strong")
FOLD_PIXELS = 200
EDGE_GUARD_PX = 3.0
TRAINING_TRACE_GUARD_PX = 2.0
H42_CAP = 2_000_000
RANDOM_SEED = 20261006


def four_colour_fold_ids(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    row_blocks = np.arange(height, dtype=np.int32) // FOLD_PIXELS
    col_blocks = np.arange(width, dtype=np.int32) // FOLD_PIXELS
    return (row_blocks[:, None] + 2 * col_blocks[None, :]) % 4


def summarize(folds: list[dict], arm_names: set[str]) -> dict[str, dict]:
    summaries = {}
    for name in sorted(arm_names):
        entries = [fold["arms"][name] for fold in folds if name in fold["arms"]]
        scores = [entry["dti"] for entry in entries]
        summaries[name] = {
            "mean_dti": round(float(np.mean(scores)), 6),
            "min_dti": round(float(np.min(scores)), 6),
            "max_dti": round(float(np.max(scores)), 6),
            "folds": len(scores),
        }
    return dict(sorted(summaries.items(), key=lambda item: (-item[1]["mean_dti"], item[0])))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--skip-cg01", action="store_true", help="reproduce H42 only")
    args = parser.parse_args()
    root = args.root.resolve()
    started = time.time()

    labels, footprint, _ = read_labels_and_footprint(root)
    if labels.shape != footprint.shape:
        raise SystemExit("labels/footprint shape mismatch")
    fold_id = four_colour_fold_ids(labels.shape)

    print("Building H42 reference surfaces from registered inputs...", flush=True)
    h42_surfaces = build_h42_surfaces(root)
    if args.skip_cg01:
        cg_score = None
        cg_valid_cells = 0
    else:
        print("Building frozen G43-CG01 cross-gradient surface...", flush=True)
        cg_score, cg_valid = build_candidate_score(root)
        if cg_score.shape != labels.shape or not np.all(np.isfinite(cg_score)):
            raise SystemExit("CG01 score has invalid shape or nonfinite cells")
        if np.count_nonzero(cg_valid & footprint) == 0:
            raise SystemExit("CG01 has no valid cells on the scoring footprint")
        cg_valid_cells = int(np.count_nonzero(cg_valid & footprint))

    with rasterio.open(root / "data/external/lidar_scarp_features_u8.tif") as scarp_src:
        scarp_hash_path = root / "data/external/lidar_scarp_features_u8.tif"
        scarp_grid_match = (
            scarp_src.shape == labels.shape
            and scarp_src.crs is not None
            and scarp_src.crs.to_epsg() == 32611
        )
    if not scarp_grid_match:
        raise SystemExit("H42 baseline scarp layer grid does not match the competition grid")

    rng_reference_random = np.random.default_rng(RANDOM_SEED)
    rng_equal_mass_random = np.random.default_rng(RANDOM_SEED + 1)
    folds: list[dict] = []
    arm_names: set[str] = set()
    for fold_number in range(4):
        fold_start = time.time()
        held = (fold_id == fold_number) & footprint
        forbidden = distance_transform_edt(~held) <= EDGE_GUARD_PX
        training = labels & ~forbidden
        evaluation = held & (distance_transform_edt(held) > EDGE_GUARD_PX)
        training_distance = distance_transform_edt(~training).astype(F32)
        allowed = evaluation & (training_distance > TRAINING_TRACE_GUARD_PX)
        eval_truth = evaluation & labels
        truth_distance = distance_transform_edt(~eval_truth)
        n_evaluation = int(evaluation.sum())
        n_truth = int(eval_truth.sum())
        arms: dict[str, dict] = {}

        def score_arm(name: str, selected: np.ndarray, note: str = "") -> None:
            result = dti(
                selected.astype(F32), labels, footprint=evaluation, truth_distance=truth_distance
            )
            if int(selected.sum()) != int(np.count_nonzero(selected & allowed)):
                raise AssertionError(f"{name}: emitted a cell outside its allowed domain")
            arms[name] = {
                "n_px": int(selected.sum()),
                "mass": float(selected.sum(dtype=np.float64)),
                "tp": round(float(result["tp"]), 2),
                "fp": round(float(result["fp"]), 2),
                "fn": round(float(result["fn"]), 2),
                "dti": round(float(result["dti"]), 6),
                "credit_per_mass": round(float(result["credit_per_mass"]), 5),
                "note": note,
            }
            arm_names.add(name)

        for surface_name in H42_SURFACES:
            surface = h42_surfaces[surface_name]
            for separation in SEPARATIONS:
                for budget in BUDGETS:
                    name = f"{surface_name}|sep{separation}|N{budget}"
                    selected = greedy_pack(surface, allowed, separation, budget, H42_CAP)
                    if int(selected.sum()) != min(budget, int(allowed.sum())):
                        raise AssertionError(f"{name}: did not satisfy declared emission budget")
                    score_arm(name, selected)
                    del selected

        # Match the public H42 20k controls exactly, then add same-domain 40k controls
        # for a strict equal-mass comparison with the candidate and selected H42 arm.
        candidate_cells = np.flatnonzero(allowed.ravel())
        if candidate_cells.size < 40_000:
            raise SystemExit(f"fold {fold_number}: fewer than 40,000 eligible cells")
        random_20k = np.zeros(labels.shape, dtype=bool)
        random_20k.ravel()[rng_reference_random.choice(candidate_cells, size=20_000, replace=False)] = True
        score_arm("CONTROL_uniform_random|N20000", random_20k,
                  "uniform random, same evaluation domain and 20k mass")
        del random_20k
        random_40k = np.zeros(labels.shape, dtype=bool)
        random_40k.ravel()[rng_equal_mass_random.choice(candidate_cells, size=40_000, replace=False)] = True
        score_arm("CONTROL_uniform_random|N40000", random_40k,
                  "uniform random, same evaluation domain and 40k mass")
        del random_40k

        density = gaussian_filter(training.astype(F32), 10)
        density[~allowed] = 0.0
        for budget in (20_000, 40_000):
            selected = greedy_pack(density, allowed, min_sep=3.0, budget=budget,
                                   candidate_cap=H42_CAP)
            score_arm(f"CONTROL_training_density|N{budget}", selected,
                      "Gaussian-smoothed training catalogue density; same mass")
            del selected
        del density

        if cg_score is not None:
            cg_allowed = allowed & cg_valid
            selected = greedy_pack(cg_score, cg_allowed, min_sep=4.0, budget=40_000,
                                   candidate_cap=H42_CAP)
            if int(selected.sum()) != 40_000:
                raise AssertionError("CG01 failed to emit the preregistered 40,000 cells")
            score_arm("G43-CG01_crossgradient|sep4.0|N40000", selected,
                      "frozen 2/4/8-px cross-gradient median; no scarp/catalogue score input")
            del selected

        fold = {
            "fold": fold_number,
            "held_cells": int(held.sum()),
            "evaluation_cells": n_evaluation,
            "evaluation_truth_pixels": n_truth,
            "training_catalogue_pixels": int(training.sum()),
            "eligible_emission_cells": int(allowed.sum()),
            "cg01_valid_eligible_cells": int(np.count_nonzero(allowed & cg_valid)) if cg_score is not None else None,
            "arms": arms,
            "seconds": round(time.time() - fold_start, 1),
        }
        folds.append(fold)
        print(
            f"fold {fold_number}: eval={n_evaluation:,}, truth={n_truth:,}, "
            f"arms={len(arms)}, elapsed={time.time()-fold_start:.1f}s",
            flush=True,
        )
        for name, stat in sorted(arms.items(), key=lambda item: -item[1]["dti"])[:5]:
            print(f"  {name:46s} dti={stat['dti']:.6f} mass={stat['mass']:.0f}", flush=True)
        del held, forbidden, training, evaluation, eval_truth, training_distance
        del truth_distance, allowed
        import gc
        gc.collect()

    summary = summarize(folds, arm_names)
    best_valid = max(
        (item for item in summary.items() if not item[0].startswith("CONTROL_")),
        key=lambda item: item[1]["mean_dti"],
    )
    selected_h42_name = "SH_basin_strong|sep4.0|N40000"
    cg_name = "G43-CG01_crossgradient|sep4.0|N40000"
    ref_path = root / "evidence/h42_holdout_owner_reference.json"
    reference = json.loads(ref_path.read_text()) if ref_path.is_file() else None
    reproduction = {"available": reference is not None, "status": "NOT_CHECKED"}
    if reference is not None:
        excluded_owner_arms = sorted(name for name in reference["summary"] if "CONTAMINATED" in name)
        reference_names = set(reference["summary"]) - set(excluded_owner_arms)
        missing_names = sorted(reference_names - set(summary))
        mismatches = []
        per_fold_ok = not missing_names
        for fold in folds:
            reference_fold = reference["folds"][fold["fold"]]["arms"]
            for name in sorted(reference_names):
                if name not in fold["arms"] or name not in reference_fold:
                    per_fold_ok = False
                    mismatches.append({"fold": fold["fold"], "arm": name, "reason": "missing"})
                    continue
                delta = abs(fold["arms"][name]["dti"] - reference_fold[name]["dti"])
                if delta > 1e-6:
                    per_fold_ok = False
                    mismatches.append({"fold": fold["fold"], "arm": name, "absolute_dti_delta": delta})
        summary_ok = True
        for name in sorted(reference_names & set(summary)):
            for key in ("mean_dti", "min_dti", "max_dti"):
                if abs(summary[name][key] - reference["summary"][name][key]) > 1e-6:
                    summary_ok = False
                    mismatches.append({"arm": name, "summary_field": key,
                                       "local": summary[name][key],
                                       "reference": reference["summary"][name][key]})
        ref = reference["summary"][selected_h42_name]
        local = summary[selected_h42_name]
        reproduction.update({
            "status": "PASS" if per_fold_ok and summary_ok else "FAIL",
            "owner_reported_mean_dti": ref["mean_dti"],
            "local_mean_dti": local["mean_dti"],
            "owner_reported_min_dti": ref["min_dti"],
            "local_min_dti": local["min_dti"],
            "owner_reported_max_dti": ref["max_dti"],
            "local_max_dti": local["max_dti"],
            "reference_arms_compared": len(reference_names),
            "owner_arms_excluded_from_reproduction": excluded_owner_arms,
            "exclusion_reason": "the owner report marks this comparison contaminated and the raster is unavailable in this checkout; it is not a clean baseline",
            "per_fold_dti_match_within_1e-6": per_fold_ok,
            "summary_match_within_1e-6": summary_ok,
            "mismatches": mismatches,
        })
    if cg_name in summary:
        local_h42 = summary[selected_h42_name]
        cg = summary[cg_name]
        fold_wins = sum(
            fold["arms"][cg_name]["dti"] > fold["arms"][selected_h42_name]["dti"]
            for fold in folds
        )
        gate = {
            "candidate": cg_name,
            "candidate_mean_dti": cg["mean_dti"],
            "h42_reproduced_mean_dti": local_h42["mean_dti"],
            "candidate_mean_beats_h42": cg["mean_dti"] > local_h42["mean_dti"],
            "fold_wins_vs_h42": int(fold_wins),
            "minimum_fold_wins_required": 3,
            "passes_holdout_promotion_gate": (
                reproduction["status"] == "PASS"
                and cg["mean_dti"] > local_h42["mean_dti"]
                and fold_wins >= 3
            ),
            "does_not_authorize_submission_without_novelty_format_provenance_and_rules_review": True,
        }
    else:
        gate = {"status": "CG01_NOT_RUN"}

    receipt = {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "design": {
            "folds": 4,
            "fold_cells": FOLD_PIXELS,
            "fold_formula": "(row//200 + 2*(col//200)) % 4",
            "outer_guard_px": EDGE_GUARD_PX,
            "training_catalogue_guard_px": TRAINING_TRACE_GUARD_PX,
            "score_domain": "held fold interior; 3-pixel edge guard",
            "equal_mass_comparison": "all model and random arms scored at N=40,000; H42 source-grid arms also reproduce all published budgets/separations",
            "seed_for_reference_random_control": RANDOM_SEED,
            "seed_for_equal_mass_random_control": RANDOM_SEED + 1,
            "truth_scope": "withheld pixels from the published catalogue; not hidden competition truth",
            "known_catalogue_mask": "not passed to the metric: held-out catalogue positives are the truth in this separate cross-validation instrument",
        },
        "provenance": {
            "h42_reference": "buffedlizard55-lab/GEMSDOE41 evidence/h42_holdout_20km.json; owner-reported scalar, included only for reproduction check",
            "h42_surface_source": "buffedlizard55-lab/GEMSDOE41 scripts/holdout_h42.py and build_h42_final.py; reimplemented locally",
            "scarp_baseline_path": str(scarp_hash_path.relative_to(root)),
            "scarp_layer_role": "H42 reproduction only; excluded from CG01",
            "candidate_inputs": ["training_features.tif band rtp", "training_features.tif band iso_grav_anom"],
            "candidate_valid_cells_on_footprint": cg_valid_cells,
            "candidate_exclusions": ["labels", "scarp features", "prior submission rasters", "leaderboard"],
        },
        "reference_reproduction": reproduction,
        "summary": summary,
        "best_valid_h42_or_candidate_arm": best_valid[0],
        "best_valid_mean_dti": best_valid[1]["mean_dti"],
        "cg01_gate": gate,
        "folds": folds,
        "interpretation_limit": (
            "This holdout tests recovery of spatially withheld published faults only. "
            "It is not an estimate or guarantee of public-board, private Phase 1, or final Phase 2 score."
        ),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    out = root / "evidence/holdout_g43_cg01.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print("\nHoldout summary (mean / minimum):")
    for name, stat in list(summary.items())[:15]:
        print(f"  {name:46s} {stat['mean_dti']:.6f} / {stat['min_dti']:.6f}")
    print(f"\nH42 reproduction: {reproduction['status']}; CG01 holdout gate: {gate}")
    print(f"Receipt: {out.relative_to(root)}")
    if reproduction["status"] == "FAIL":
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
