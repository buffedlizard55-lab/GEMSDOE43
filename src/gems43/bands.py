"""Readers for the 19 official bands and the hash-pinned external rasters.

Band names are read from the GeoTIFF band descriptions of ``training_features.tif`` -- they are
never hard-coded from memory.  The float32 sentinel ``-3.4028234663852886e+38`` (the declared
``nodata``) is replaced by NaN and then gap-filled by nearest-valid-value inside the footprint,
which is the defect that produced the portal error "Predicted values must be in range [0, 1]"
(documented in ``docs/research/range-error-root-cause.md`` of the parent project).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from . import paths

BAND_NAMES: list[str] | None = None
SENTINEL = -3.4028234663852886e38


def raw_path(name: str) -> Path:
    p = paths.data_dir() / name
    if not p.exists():
        raise FileNotFoundError(
            f"{p} missing -- run `bash scripts/fetch_mirrors.sh` first "
            f"(or set GEMS_DATA_DIR)."
        )
    return p


def band_descriptions() -> list[str]:
    """The organizer's own band descriptions, read from the file (never assumed)."""
    with rasterio.open(raw_path("training_features.tif")) as src:
        return list(src.descriptions)


def footprint() -> np.ndarray:
    """Boolean (H, W) scoring footprint = the finite cells of ``sample_submission.tif``."""
    cache = paths.work_dir() / "footprint.npy"
    if cache.exists():
        return np.load(cache)
    with rasterio.open(raw_path("sample_submission.tif")) as src:
        a = src.read(1)
    foot = np.isfinite(a)
    paths.work_dir().mkdir(parents=True, exist_ok=True)
    np.save(cache, foot)
    return foot


def catalogue() -> np.ndarray:
    """Boolean (H, W) of the published USGS/INGENIOUS fault pixels (``labels.tif == 1``)."""
    cache = paths.work_dir() / "catalogue.npy"
    if cache.exists():
        return np.load(cache)
    with rasterio.open(raw_path("labels.tif")) as src:
        lab = src.read(1)
    cat = lab == 1
    paths.work_dir().mkdir(parents=True, exist_ok=True)
    np.save(cache, cat)
    return cat


def _fill(foot: np.ndarray, band: np.ndarray) -> np.ndarray:
    """Replace the sentinel with NaN, then nearest-valid-value fill inside the footprint."""
    a = band.astype(np.float32, copy=True)
    bad = ~np.isfinite(a) | (np.abs(a - SENTINEL) < 1e30)
    a[bad] = np.nan
    valid = ~bad
    if bad.any():
        idx = distance_transform_edt(~valid, return_distances=False, return_indices=True)
        a[bad] = a[tuple(idx[:, bad])]
    # Anything still non-finite (a band valid nowhere) falls back to zero outside the footprint.
    a[~np.isfinite(a)] = 0.0
    a[~foot] = 0.0
    return a.astype(np.float32)


def band(name: str) -> np.ndarray:
    """One official band, sentinel-cleaned and gap-filled, as float32 on the frozen grid."""
    names = band_descriptions()
    key = [n.split(" - ")[0].strip() for n in names]
    if name not in key:
        raise KeyError(f"band {name!r} not in {key}")
    i = key.index(name) + 1
    cache = paths.bands_dir() / f"{name}.npy"
    if cache.exists():
        return np.load(cache)
    with rasterio.open(raw_path("training_features.tif")) as src:
        a = src.read(i)
    filled = _fill(footprint(), a)
    np.save(cache, filled)
    return filled


def all_bands() -> dict[str, np.ndarray]:
    return {n.split(" - ")[0].strip(): band(n.split(" - ")[0].strip())
            for n in band_descriptions()}


def external(name: str):
    """A hash-pinned external raster (uint8 stack) or CSV, loaded lazily."""
    p = paths.data_dir() / "external" / name
    if not p.exists():
        raise FileNotFoundError(p)
    if p.suffix == ".tif":
        with rasterio.open(p) as src:
            return src.read(), list(src.descriptions)
    raise ValueError(p)


def dist_to_catalogue_px() -> np.ndarray:
    """Exact Euclidean distance (in 100 m pixels) from every cell to the nearest catalogue pixel."""
    cache = paths.work_dir() / "dist_cat.npy"
    if cache.exists():
        return np.load(cache)
    d = distance_transform_edt(~catalogue()).astype(np.float32)
    np.save(cache, d)
    return d


def points_from_csv(name: str, row_col: tuple[str, str] = ("row", "col")):
    """Row/col point table from a GDR CSV in the data root's ``external/`` folder."""
    import pandas as pd

    df = pd.read_csv(paths.data_dir() / "external" / name)
    return df
