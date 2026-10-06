#!/usr/bin/env python3
"""Build the round-2 full-footprint submission GeoTIFF for the winning arm.

Reads the primary arm from evidence/holdout_g43_mclp.json (or --arm to override),
rebuilds its surface on the full footprint, emits exactly 40,000 binary dots on
cells more than 2 px from any catalogue positive (consistent with the holdout's
2-px training guard; on-catalogue pixels are masked inert under official scoring),
and writes the `-nan` primary plus `-zeros` fallback twin into docs/downloads/.
Each file is independently re-read by scripts/audit_submission.py; the build fails
unless both audits PASS (format + novelty vs the prior corpus).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from audit_submission import audit  # noqa: E402
from gemsdoe43.density import geometric_mean, greedy_pack  # noqa: E402
from gemsdoe43.h42 import build_h42_surfaces  # noqa: E402
from gemsdoe43.io import read_labels_and_footprint  # noqa: E402
from gemsdoe43.mclp import lazy_greedy_cover  # noqa: E402
from gemsdoe43.sup01 import fit_predict_in_sample, load_feature_stack  # noqa: E402
from gemsdoe43.surfaces import build_mg01_surface  # noqa: E402

F32 = np.float32
BUDGET = 40_000
CANDIDATE_CAP = 300_000
H42_CAP = 2_000_000
DOWNLOADS = ROOT / "docs/downloads"

ARM_SURFACE = {
    "D_SUP01_HGB|sep4.0|N40000": ("sup01", "packing"),
    "E_ENS_SH_MG01|sep4.0|N40000": ("ens", "packing"),
    "B_MG01_MCLP|N40000": ("mg01", "mclp"),
    "A_SH_MCLP|N40000": ("sh", "mclp"),
}


def content_id(selected: np.ndarray) -> str:
    flat = np.flatnonzero(selected.ravel()).astype(np.int64)
    return hashlib.sha256(flat.tobytes()).hexdigest()[:12]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", type=str, default=None)
    parser.add_argument("--receipt", type=Path,
                        default=ROOT / "evidence/holdout_g43_mclp.json")
    parser.add_argument("--stamp", type=str, default="20261006")
    args = parser.parse_args()

    holdout = json.loads(args.receipt.read_text(encoding="utf-8"))
    arm = args.arm or holdout.get("primary_arm")
    if arm not in ARM_SURFACE:
        raise SystemExit(f"no buildable primary arm (got {arm!r}); "
                         f"pass --arm explicitly to build a research artifact")
    surface_kind, emitter = ARM_SURFACE[arm]
    gate = holdout.get("gate", {}).get(arm, {})
    slot_eligible = bool(gate.get("passes_holdout_promotion_gate"))

    known, footprint, _ = read_labels_and_footprint(ROOT)
    catdist = distance_transform_edt(~known).astype(F32)

    if surface_kind == "sup01":
        import gc as _gc

        stack, bands_valid, feature_names = load_feature_stack(ROOT)
        valid = footprint & bands_valid
        train_cells = np.flatnonzero(valid.ravel())
        train_labels = known.ravel()[train_cells]
        print(f"SUP01 full build: training on {train_cells.size:,} cells "
              f"({int(known.sum()):,} positives)...", flush=True)
        matrix = np.ascontiguousarray(stack[train_cells])
        del stack
        _gc.collect()
        t0 = time.time()
        proba, sup_info = fit_predict_in_sample(matrix, train_labels)
        print(f"SUP01 trained in {time.time()-t0:.0f}s, n_iter={sup_info['n_iter']}",
              flush=True)
        surface = np.zeros(known.shape, dtype=F32)
        surface.ravel()[train_cells] = proba
        del matrix, proba, train_labels
        _gc.collect()
    elif surface_kind == "ens":
        sh = build_h42_surfaces(ROOT)["SH_basin_strong"]
        mg, mg_valid = build_mg01_surface(ROOT)
        surface = geometric_mean({"sh": sh, "mg": mg}, {"sh": 0.5, "mg": 0.5})
        surface[~mg_valid] = 0.0
        valid = footprint & mg_valid
        sup_info, feature_names = {}, []
    elif surface_kind == "mg01":
        surface, valid = build_mg01_surface(ROOT)
        valid = footprint & valid
        sup_info, feature_names = {}, []
    else:
        surface = build_h42_surfaces(ROOT)["SH_basin_strong"]
        valid = footprint.copy()
        sup_info, feature_names = {}, []

    eligible = valid & (catdist > 2.0)
    print(f"Eligible cells (valid & d>2px from catalogue): {int(eligible.sum()):,}",
          flush=True)
    if int(eligible.sum()) < BUDGET:
        raise SystemExit("fewer eligible cells than the budget")

    if emitter == "packing":
        selected = greedy_pack(surface, eligible, min_sep=4.0, budget=BUDGET,
                               candidate_cap=H42_CAP)
        emit_info = {"emitter": "greedy_pack", "min_sep": 4.0}
    else:
        demand = np.where(valid, surface.astype(np.float64), 0.0)
        t0 = time.time()
        selected, stats = lazy_greedy_cover(demand, eligible, budget=BUDGET,
                                            candidate_cap=CANDIDATE_CAP)
        emit_info = {"emitter": "lazy_greedy_cover", "candidate_cap": CANDIDATE_CAP,
                     "objective": round(stats["objective"], 3),
                     "recomputes": stats["recomputes"],
                     "seconds": round(time.time() - t0, 1)}
    if int(selected.sum()) != BUDGET:
        raise SystemExit("emission did not satisfy the budget")
    if np.count_nonzero(selected & known) or np.count_nonzero(selected & (catdist <= 2.0)):
        raise SystemExit("emitted a catalogue-adjacent cell")

    cid = content_id(selected)
    tag = {"D_SUP01_HGB|sep4.0|N40000": "sup01-hgb21-sep40",
           "E_ENS_SH_MG01|sep4.0|N40000": "ens-sh-mg01-sep40",
           "B_MG01_MCLP|N40000": "mg01-mclp",
           "A_SH_MCLP|N40000": "sh-mclp"}[arm]
    stem = f"gems43-{tag}-n{BUDGET}-{args.stamp}-{cid}"
    DOWNLOADS.mkdir(parents=True, exist_ok=True)

    with rasterio.open(ROOT / "data/sample_submission.tif") as template:
        profile = template.profile.copy()
    profile.update(driver="GTiff", count=1, dtype="float32", compress="deflate")
    nan_path = DOWNLOADS / f"{stem}-nan.tif"
    arr = np.where(selected, 1.0, 0.0).astype(F32)
    arr[~footprint] = np.nan
    profile.update(nodata=np.nan)
    with rasterio.open(nan_path, "w", **profile) as dst:
        dst.write(arr, 1)
    zeros_path = DOWNLOADS / f"{stem}-zeros.tif"
    arr0 = np.where(selected, 1.0, 0.0).astype(F32)
    arr0[~footprint] = 0.0
    profile.update(nodata=None)
    with rasterio.open(zeros_path, "w", **profile) as dst:
        dst.write(arr0, 1)

    nan_audit = audit(nan_path, ROOT / "data/prior_corpus", BUDGET)
    zeros_audit = audit(zeros_path, ROOT / "data/prior_corpus", BUDGET)
    (DOWNLOADS / f"{stem}-nan-audit.json").write_text(
        json.dumps(nan_audit, indent=2) + "\n", encoding="utf-8")
    (DOWNLOADS / f"{stem}-zeros-audit.json").write_text(
        json.dumps(zeros_audit, indent=2) + "\n", encoding="utf-8")
    print(f"nan audit: {nan_audit['result']} sha256={nan_audit['sha256'][:16]}... "
          f"ones={nan_audit['ones']}")
    print(f"zeros audit: {zeros_audit['result']} sha256={zeros_audit['sha256'][:16]}... "
          f"ones={zeros_audit['ones']}")
    if nan_audit["result"] != "PASS" or zeros_audit["result"] != "PASS":
        raise SystemExit("submission audit FAILED; files are not releasable")

    build_receipt = {
        "schema_version": 1,
        "arm": arm,
        "surface": surface_kind,
        "emission": emit_info,
        "budget": BUDGET,
        "slot_eligible_per_gate": slot_eligible,
        "gate": gate,
        "live_score": None,
        "live_status": "UNSCRED",
        "sup01": sup_info,
        "sup01_features": feature_names,
        "files": {
            "nan": {"name": nan_path.name, "sha256": nan_audit["sha256"],
                    "bytes": nan_audit["bytes"]},
            "zeros": {"name": zeros_path.name, "sha256": zeros_audit["sha256"],
                      "bytes": zeros_audit["bytes"]},
        },
        "novelty": nan_audit["novelty_vs_corpus"],
    }
    (DOWNLOADS / f"{stem}-build.json").write_text(
        json.dumps(build_receipt, indent=2) + "\n", encoding="utf-8")
    status = {
        "schema_version": 1,
        "as_of_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "candidate": stem,
        "arm": arm,
        "status": "SLOT_ELIGIBLE" if slot_eligible else "RESEARCH_ARTIFACT_NOT_SLOT_RECOMMENDED",
        "live_status": "UNSCRED",
        "primary_file": f"docs/downloads/{nan_path.name}",
        "fallback_file": f"docs/downloads/{zeros_path.name}",
        "unique_submission_name": None,  # set by the site update once results land
        "portal_comment": None,
    }
    (ROOT / "evidence/submission_status.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8")
    print(f"Built {stem} slot_eligible={slot_eligible}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
