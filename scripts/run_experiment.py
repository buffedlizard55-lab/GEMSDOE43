#!/usr/bin/env python3
"""Run the source-gated H46-B vs H42 holdout and emit a unique research GeoTIFF."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe43.experiment_sgmc import run_experiment  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--lidar", type=Path, required=True)
    p.add_argument("--sgmc-ca", type=Path, required=True)
    p.add_argument("--sgmc-nv", type=Path, required=True)
    p.add_argument("--sgmc-tables", type=Path, required=True)
    p.add_argument("--submission-out", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, default=ROOT / "evidence" / "h46b")
    args = p.parse_args()
    report = run_experiment(
        features_path=args.features,
        labels_path=args.labels,
        template_path=args.template,
        lidar_path=args.lidar,
        ca_zip_path=args.sgmc_ca,
        nv_zip_path=args.sgmc_nv,
        tables_zip_path=args.sgmc_tables,
        submission_path=args.submission_out,
        evidence_dir=args.evidence_dir,
    )
    result = report["holdout"]
    print(json.dumps({
        "experiment_id": report["experiment_id"],
        "h42_mean_dti": result["incumbent_prior_reference"]["same_run_mean_dti"],
        "h46b_mean_dti": result["h46b"]["mean_dti"],
        "mean_delta": result["h46b"]["mean_delta_vs_same_run_incumbent"],
        "fold_deltas": result["h46b"]["fold_deltas"],
        "local_gate_passed": result["promotion_gate"]["gate_passed"],
        "submission_slot_authorized": result["promotion_gate"]["submission_slot_authorized"],
        "submission": report["submission"],
    }, indent=2))


if __name__ == "__main__":
    main()
