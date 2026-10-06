#!/usr/bin/env python3
"""Run the locked H46-A vs H42 holdout and emit a new, research-only GeoTIFF."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe43.experiment import run_experiment  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--features", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--template", type=Path, required=True)
    p.add_argument("--lidar", type=Path, required=True)
    p.add_argument("--csv", type=Path, required=True)
    p.add_argument("--submission-out", type=Path, required=True)
    p.add_argument("--evidence-dir", type=Path, default=ROOT / "evidence")
    args = p.parse_args()
    report = run_experiment(
        features_path=args.features,
        labels_path=args.labels,
        template_path=args.template,
        lidar_path=args.lidar,
        csv_path=args.csv,
        submission_path=args.submission_out,
        evidence_dir=args.evidence_dir,
    )
    print(json.dumps({
        "experiment_id": report["experiment_id"],
        "h42_mean_dti": report["holdout"]["incumbent_prior_reference"]["same_run_mean_dti"],
        "h46a_mean_dti": report["holdout"]["h46a"]["mean_dti"],
        "mean_delta": report["holdout"]["h46a"]["mean_delta_vs_same_run_incumbent"],
        "local_gate_passed": report["holdout"]["promotion_gate"]["gate_passed"],
        "submission_slot_authorized": report["holdout"]["promotion_gate"]["submission_slot_authorized"],
        "submission": report["submission"],
    }, indent=2))


if __name__ == "__main__":
    main()
