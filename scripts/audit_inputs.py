#!/usr/bin/env python3
"""Byte-independent metadata and footprint audit for restored GEMS input rasters."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def raster_meta(path: Path) -> dict:
    with rasterio.open(path) as ds:
        return {
            "path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": file_sha256(path),
            "driver": ds.driver,
            "count": ds.count,
            "dtypes": list(ds.dtypes),
            "shape": [ds.height, ds.width],
            "crs": ds.crs.to_string() if ds.crs else None,
            "transform": [float(v) for v in ds.transform[:6]],
            "bounds": [float(ds.bounds.left), float(ds.bounds.bottom), float(ds.bounds.right), float(ds.bounds.top)],
            "nodata": None if ds.nodata is None else (float(ds.nodata) if np.isfinite(ds.nodata) else str(ds.nodata)),
            "tags": ds.tags(),
            "bands": [ds.tags(i) for i in range(1, ds.count + 1)],
        }


def main() -> int:
    features_path = DATA / "training_features.tif"
    labels_path = DATA / "labels.tif"
    sample_path = DATA / "sample_submission.tif"
    scarp_path = DATA / "external/lidar_scarp_features_u8.tif"
    for path in (features_path, labels_path, sample_path, scarp_path):
        if not path.is_file():
            raise SystemExit(f"missing {path.relative_to(ROOT)}; run bash scripts/download_competition_data.sh")

    features = raster_meta(features_path)
    labels_meta = raster_meta(labels_path)
    sample_meta = raster_meta(sample_path)
    scarp_meta = raster_meta(scarp_path)

    with rasterio.open(sample_path) as ds:
        sample = ds.read(1)
        footprint = np.isfinite(sample)
    with rasterio.open(labels_path) as ds:
        labels = ds.read(1)
    with rasterio.open(features_path) as ds:
        band_audits = []
        sentinel = ds.nodata
        names = []
        for index in range(1, ds.count + 1):
            tags = ds.tags(index)
            name = tags.get("band_name", f"band_{index}")
            names.append(name)
            values = ds.read(index)
            valid = np.isfinite(values)
            if sentinel is not None and np.isfinite(sentinel) and sentinel < -1e30:
                valid &= values > -1e30
            band_audits.append({
                "index_1_based": index,
                "band_name": name,
                "description": tags.get("description"),
                "valid_on_footprint": int(np.count_nonzero(valid & footprint)),
                "invalid_on_footprint": int(np.count_nonzero(~valid & footprint)),
                "valid_outside_footprint": int(np.count_nonzero(valid & ~footprint)),
                "finite_min_valid": float(values[valid & footprint].min()) if np.any(valid & footprint) else None,
                "finite_max_valid": float(values[valid & footprint].max()) if np.any(valid & footprint) else None,
            })

    with rasterio.open(scarp_path) as ds:
        scarp = ds.read(1)
        scarp_footprint = np.isfinite(scarp) & (scarp != ds.nodata if ds.nodata is not None else True)

    geometry = lambda x: (x["shape"], x["crs"], x["transform"])
    assert geometry(features) == geometry(labels_meta) == geometry(sample_meta), "competition raster grid mismatch"
    assert int(footprint.sum()) == 5_167_373, "unexpected sample finite-footprint size"
    assert labels.shape == sample.shape
    assert set(np.unique(labels).tolist()) <= {-1, 0, 1}

    positive = labels == 1
    sample_ones = np.isfinite(sample) & (sample == 1.0)
    label_outside = labels == -1
    irregularities = []
    if not np.array_equal(label_outside, ~footprint):
        irregularities.append({"id": "IR-DATA-02", "finding": "label -1 mask does not exactly match sample NaN footprint"})
    if int(positive.sum()) == int(sample_ones.sum()) and np.array_equal(positive, sample_ones):
        irregularities.append({
            "id": "IR-DATA-01",
            "finding": "sample_submission has 60,988 values of 1 exactly on all known-label positives; it is not all-zero in this mirror",
            "action": "use sample_submission values only for grid/footprint; never copy its predictions",
        })
    if geometry(scarp_meta) != geometry(sample_meta):
        irregularities.append({"id": "IR-DATA-03", "finding": "baseline scarp raster is not on the exact competition grid; do not use until warped and audited"})
    if len(names) != len(set(names)):
        raise AssertionError("duplicate feature band_name tags")
    for required in ("rtp", "iso_grav_anom"):
        if names.count(required) != 1:
            raise AssertionError(f"expected exactly one band named {required!r}, found {names.count(required)}")

    receipt = {
        "schema_version": 1,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source_authentication": "owner-published mirror; hash-verified against registry/data_sources.json; not organizer-authenticated",
        "grid": {
            "shape": list(sample.shape),
            "crs": sample_meta["crs"],
            "transform": sample_meta["transform"],
            "finite_sample_footprint_cells": int(footprint.sum()),
            "outside_footprint_cells": int((~footprint).sum()),
        },
        "features": features,
        "feature_band_validity": band_audits,
        "labels": {
            "metadata": labels_meta,
            "positive_pixels": int(positive.sum()),
            "zero_pixels": int(np.count_nonzero(labels == 0)),
            "outside_pixels": int(label_outside.sum()),
        },
        "sample_submission": {
            "metadata": sample_meta,
            "finite_pixels": int(footprint.sum()),
            "nan_pixels": int(np.isnan(sample).sum()),
            "one_pixels": int(sample_ones.sum()),
            "equals_label_positive_mask": bool(np.array_equal(sample_ones, positive)),
        },
        "baseline_only_lidar_scarp": {
            "metadata": scarp_meta,
            "valid_cells": int(scarp_footprint.sum()),
            "exact_grid_match": geometry(scarp_meta) == geometry(sample_meta),
            "used_in_candidate": False,
        },
        "irregularities": irregularities,
        "result": "PASS" if len(irregularities) == 1 and irregularities[0]["id"] == "IR-DATA-01" else "REVIEW",
    }
    out = ROOT / "evidence/input_audit.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Input audit: {receipt['result']} -> {out.relative_to(ROOT)}")
    print(f"Grid: {sample.shape[1]}x{sample.shape[0]} {sample_meta['crs']} | foot={footprint.sum():,} | outside={(~footprint).sum():,}")
    print(f"Labels: {positive.sum():,} positives | sample: {sample_ones.sum():,} ones (same mask={np.array_equal(sample_ones, positive)})")
    for item in irregularities:
        print(f"{item['id']}: {item['finding']}")
    return 0 if receipt["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
