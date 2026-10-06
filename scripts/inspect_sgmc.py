#!/usr/bin/env python3
"""Audit official USGS SGMC polygon coverage and categorical attributes (no labels read)."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import rasterio
from gemsdoe43.geology import contact_contrast, load_sgmc_unit_raster, source_viability_gates


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ca-zip", type=Path, required=True)
    parser.add_argument("--nv-zip", type=Path, required=True)
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    archives = {"CA": args.ca_zip, "NV": args.nv_zip}
    try:
        for state, path in archives.items():
            if not path.is_file():
                raise FileNotFoundError(f"Missing official SGMC {state} archive: {path}")
        with rasterio.open(args.template) as src:
            # The mirrored template is label-contaminated; only finite area and grid metadata
            # are used. Its finite pixel values are never interpreted as scores or labels.
            values = src.read(1)
            footprint = np.isfinite(values)
            if src.nodata is not None and np.isfinite(src.nodata):
                footprint &= values != np.float32(src.nodata)
            shape = (src.height, src.width)
            transform = src.transform
            crs = src.crs
            grid = {
                "height": src.height,
                "width": src.width,
                "crs": crs.to_string() if crs else None,
                "transform": [float(v) for v in tuple(src.transform)[:6]],
                "bounds": [float(src.bounds.left), float(src.bounds.bottom),
                           float(src.bounds.right), float(src.bounds.top)],
                "footprint_cells": int(footprint.sum()),
            }
        if crs is None or crs.to_epsg() != 32611:
            raise ValueError(f"Expected template CRS EPSG:32611, got {crs}")

        geology = load_sgmc_unit_raster(
            archives,
            out_shape=shape,
            transform=transform,
            target_crs=crs,
            bounds=grid["bounds"],
        )
        strength, contrast_report = contact_contrast(geology.unit_id, geology, footprint)
        gates = source_viability_gates(contrast_report)
        archive_receipts = {
            state: {
                "url": f"https://mrdata.usgs.gov/geology/state/shp/{state}.zip",
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for state, path in archives.items()
        }
        summary = {
            "source": "USGS State Geologic Map Compilation (SGMC), version 1.1; state polygon/attribute archives",
            "source_release_doi": "https://doi.org/10.5066/F7WH2N65",
            "source_metadata": "https://mrdata.usgs.gov/geology/state/USGS_SGMC_Metadata.html",
            "archive_receipts": archive_receipts,
            "template_sha256": sha256(args.template),
            "template_grid": grid,
            "polygon_rasterization": geology.report,
            "contact_contrast_audit": contrast_report,
            "data_viability_gates": gates,
            "all_data_viability_gates_pass": all(gates.values()),
            "interpretation": "Official-source, schema, polygon-coverage and support audit only; not a fault score or holdout result.",
            "label_access": "No labels or sample-template pixel values were read; finite mask and grid metadata only.",
        }
        exit_code = 0
    except Exception as exc:
        summary = {
            "audit_error_type": type(exc).__name__,
            "audit_error": str(exc),
            "traceback": traceback.format_exc(),
            "source_paths": {state: str(path) for state, path in archives.items()},
            "source_files": {
                state: {
                    "exists": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else None,
                    "sha256": sha256(path) if path.exists() else None,
                }
                for state, path in archives.items()
            },
            "template_path": str(args.template),
            "template_exists": args.template.exists(),
        }
        exit_code = 2
    args.out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
