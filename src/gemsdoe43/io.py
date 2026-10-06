"""Raster I/O helpers that preserve the competition grid and mask semantics."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"


def read_band_with_mask(path: Path, band: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """Read a float32 band and preserve its validity mask before replacing nodata by 0."""
    with rasterio.open(path) as src:
        if not 1 <= band <= src.count:
            raise ValueError(f"band {band} is outside 1..{src.count} for {path}")
        arr = src.read(band).astype(np.float32, copy=False)
        nodata = src.nodata
    valid = np.isfinite(arr)
    if nodata is not None and np.isfinite(nodata):
        valid &= arr != np.float32(nodata)
    valid &= arr > -1e37
    if not valid.all():
        arr = arr.copy()
        arr[~valid] = 0.0
    return arr, valid


def read_band(path: Path, band: int = 1) -> np.ndarray:
    """Read a band as float32; turn NaN and the competition's huge nodata sentinel to 0."""
    return read_band_with_mask(path, band)[0]


def read_named_band(path: Path, band_name: str) -> tuple[np.ndarray, np.ndarray]:
    """Locate a raster band by its `band_name` tag and return values plus valid mask."""
    with rasterio.open(path) as src:
        matches = [
            index for index in range(1, src.count + 1)
            if src.tags(index).get("band_name") == band_name
        ]
    if len(matches) != 1:
        raise ValueError(f"expected one band named {band_name!r}, found {matches}")
    return read_band_with_mask(path, matches[0])


def read_labels_and_footprint(root: Path = ROOT) -> tuple[np.ndarray, np.ndarray, dict]:
    """Load known positive catalogue cells and the sample's finite area footprint.

    `sample_submission.tif` values are never used as predictions; only its finite mask
    and georeferencing are read. Its mirrored positive values coincide with all known
    labels, an irregularity recorded in evidence/input_audit.json.
    """
    with rasterio.open(root / "data/labels.tif") as labels_src:
        raw_labels = labels_src.read(1)
        label_profile = labels_src.profile.copy()
        label_grid = (labels_src.crs, labels_src.transform, labels_src.shape)
    known_faults = raw_labels == 1
    with rasterio.open(root / "data/sample_submission.tif") as sample_src:
        sample = sample_src.read(1)
        footprint = np.isfinite(sample)
        sample_grid = (sample_src.crs, sample_src.transform, sample_src.shape)
    if label_grid != sample_grid:
        raise ValueError("labels and sample_submission grids do not match")
    if not np.all(np.isin(raw_labels, (-1, 0, 1))):
        raise ValueError("labels contain values outside {-1,0,1}")
    return known_faults, footprint, label_profile


def assert_competition_grid(*paths: Path) -> None:
    """Raise unless all given rasters share the same CRS, transform and dimensions."""
    reference = None
    for path in paths:
        with rasterio.open(path) as src:
            grid = (src.crs, src.transform, src.width, src.height)
        if reference is None:
            reference = grid
        elif grid != reference:
            raise ValueError(f"grid mismatch: {path} differs from {paths[0]}")
