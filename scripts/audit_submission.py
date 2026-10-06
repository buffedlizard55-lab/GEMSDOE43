#!/usr/bin/env python3
"""Independent format + novelty audit for a G43 submission GeoTIFF.

Re-reads the file from disk and checks the portal contract (single-band float32,
EPSG:32611, 100-m grid, matching shape/geotransform, [0,1] inside, NaN outside for
`-nan` variants / all-finite zeros for `-zeros` twins) plus novelty against the
prior-submission corpus in data/prior_corpus/. Exits nonzero on any failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe43.io import read_labels_and_footprint  # noqa: E402

EXPECTED_SHAPE = (3730, 3292)
EXPECTED_CRS = "EPSG:32611"
EXPECTED_TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
JACCARD_DUPLICATE_THRESHOLD = 0.80
OVERLAP_DUPLICATE_THRESHOLD = 0.90


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def audit(path: Path, corpus_dir: Path, budget: int = 40_000) -> dict:
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "pass": bool(passed), "detail": detail})
        if not passed:
            print(f"FAIL {name}: {detail}", flush=True)

    known, footprint, _ = read_labels_and_footprint(ROOT)
    with rasterio.open(path) as src:
        profile = src.profile.copy()
        crs = src.crs
        transform = src.transform
        count, dtypes = src.count, src.dtypes
        nodata = src.nodata
        arr = src.read(1)
    finite = np.isfinite(arr)
    inside = finite & footprint
    n_ones = int(np.count_nonzero(finite & (arr == 1.0)))

    check("file_exists", path.is_file(), str(path))
    check("single_band", count == 1, f"count={count}")
    check("dtype_float32", list(dtypes) == ["float32"], f"dtypes={dtypes}")
    check("crs_epsg_32611", crs is not None and crs.to_epsg() == 32611, str(crs))
    check("shape_matches", arr.shape == EXPECTED_SHAPE, f"shape={arr.shape}")
    check("transform_matches", tuple(float(v) for v in transform[:6]) == EXPECTED_TRANSFORM,
          f"transform={tuple(transform[:6])}")
    is_nan_variant = path.stem.endswith("-nan")
    is_zeros_variant = path.stem.endswith("-zeros")
    check("named_variant", is_nan_variant != is_zeros_variant, path.name)
    if is_nan_variant:
        check("nan_outside_matches_footprint", bool(np.array_equal(~finite, ~footprint)),
              f"nan={int((~finite).sum())} outside={int((~footprint).sum())}")
        check("nodata_is_nan", nodata is not None and np.isnan(nodata), f"nodata={nodata}")
    if is_zeros_variant:
        check("all_finite", bool(np.all(finite)), f"nan={int((~finite).sum())}")
        check("zeros_outside", bool(np.all(arr[~footprint] == 0.0)))
        check("no_nodata_tag", nodata is None, f"nodata={nodata}")
    check("finite_inside", int(np.count_nonzero(~finite & footprint)) == 0)
    inside_values = arr[footprint]
    check("range_inside_01",
          bool(np.all(inside_values >= 0.0) and np.all(inside_values <= 1.0)),
          f"min={float(inside_values.min())} max={float(inside_values.max())}")
    check("binary_inside", bool(np.all(np.isin(inside_values, (0.0, 1.0)))),
          f"unique={np.unique(inside_values)[:8]}")
    check("emission_budget", n_ones == budget, f"ones={n_ones} budget={budget}")
    check("zero_on_catalogue", int(np.count_nonzero((arr == 1.0) & known)) == 0)
    result = {
        "schema_version": 1,
        "file": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "profile": {key: str(value) for key, value in profile.items()},
        "ones": n_ones,
        "checks": checks,
    }

    novelty = []
    ones = (arr == 1.0) & finite
    for prior in sorted(corpus_dir.glob("*.tif")):
        with rasterio.open(prior) as src:
           parr = src.read(1)
        pones = (parr == 1.0) & np.isfinite(parr)
        inter = int(np.count_nonzero(ones & pones))
        union = int(np.count_nonzero(ones | pones))
        jaccard = inter / union if union else 0.0
        overlap = inter / min(n_ones, int(pones.sum())) if min(n_ones, int(pones.sum())) else 0.0
        entry = {
            "prior": prior.name,
            "prior_ones": int(pones.sum()),
            "intersection": inter,
            "jaccard": round(jaccard, 6),
            "overlap_coefficient": round(overlap, 6),
            "same_sha256": sha256(prior) == result["sha256"],
        }
        novelty.append(entry)
        check(f"novelty_jaccard_vs_{prior.stem}", jaccard < JACCARD_DUPLICATE_THRESHOLD,
              f"jaccard={jaccard:.4f}")
        check(f"novelty_overlap_vs_{prior.stem}", overlap < OVERLAP_DUPLICATE_THRESHOLD,
              f"overlap={overlap:.4f}")
        check(f"novelty_hash_vs_{prior.stem}", not entry["same_sha256"])
    result["novelty_vs_corpus"] = novelty
    result["result"] = "PASS" if all(item["pass"] for item in checks) else "FAIL"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tif", type=Path)
    parser.add_argument("--corpus", type=Path, default=ROOT / "data/prior_corpus")
    parser.add_argument("--budget", type=int, default=40_000)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    result = audit(args.tif, args.corpus, args.budget)
    out = args.out or args.tif.with_name(args.tif.stem + "-audit.json")
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Audit {result['result']}: {args.tif.name} ones={result['ones']} "
          f"sha256={result['sha256'][:16]}... receipt={out.name}")
    return 0 if result["result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
