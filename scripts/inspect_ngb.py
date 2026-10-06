#!/usr/bin/env python3
"""Audit the official USGS NGB CSV against the competition footprint (no labels read)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import rasterio
from gemsdoe43.geochem import project_to_template, read_ngb_csv, rasterize_local_enrichment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    raw = read_ngb_csv(args.csv)
    with rasterio.open(args.template) as src:
        # The template's cell values (which mirror labels in this owner-supplied copy) are
        # deliberately never inspected; only its finite-area mask and georeferencing are read.
        footprint = np.isfinite(src.read(1))
        shape = src.height, src.width
    all_mapped, spatial_all = project_to_template(
        raw.samples, args.template, footprint, require_index=False
    )
    valid_mapped, spatial_valid = project_to_template(
        raw.samples, args.template, footprint, require_index=True
    )
    field, support, field_report = rasterize_local_enrichment(
        valid_mapped, shape, footprint, sigma_px=20.0
    )
    gates = {
        "at_least_1000_eligible_stream_sample_locations_in_footprint": (
            spatial_all["samples_in_footprint"] >= 1000
        ),
        "at_least_500_samples_with_ge3_assays_in_footprint": (
            spatial_valid["samples_in_footprint"] >= 500
        ),
        "geochemical_support_nonempty": bool(np.any(support)),
        "source_crs_transformed_to_template_crs": (
            spatial_all["source_crs_assumption"] == "EPSG:4267"
            and spatial_all["target_crs"] == "EPSG:32611"
        ),
        "all_inside_footprint_field_values_finite_and_bounded": bool(
            np.isfinite(field[footprint]).all()
            and np.all((field[footprint] >= 0) & (field[footprint] <= 1))
        ),
        "outside_footprint_field_zero": bool(np.all(field[~footprint] == 0)),
    }
    summary = {
        "source": "USGS Open-File Report 2002-227; official ngb.csv HTTPS endpoint",
        "source_url": "https://pubs.usgs.gov/of/2002/0227/ngb.csv",
        "source_sha256": hashlib.sha256(args.csv.read_bytes()).hexdigest(),
        "source_bytes": args.csv.stat().st_size,
        "template_sha256": hashlib.sha256(args.template.read_bytes()).hexdigest(),
        "sample_count_report": raw.report,
        "all_stream_sample_spatial_coverage_report": spatial_all,
        "geochem_eligible_sample_spatial_coverage_report": spatial_valid,
        "fixed_2km_rasterization_report": field_report,
        "data_viability_gates": gates,
        "all_data_viability_gates_pass": all(gates.values()),
        "interpretation": "Source/data quality audit only; not a fault score or holdout result.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
