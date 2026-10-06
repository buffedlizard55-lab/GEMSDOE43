"""Shared deterministic surfaces and emission packing for H42/H46-A comparison."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

F32 = np.float32
GEOMETRIC_MEAN_FLOOR = 0.05


def read_band(path: str | Path, band: int = 1) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as src:
        out = src.read(band).astype(F32, copy=False)
        nodata = src.nodata
    invalid = ~np.isfinite(out)
    if nodata is not None and math.isfinite(float(nodata)):
        invalid |= out == F32(nodata)
    invalid |= out < F32(-1e37)
    if invalid.any():
        out = out.copy()
        out[invalid] = F32(0.0)
    return out


def smooth(x: np.ndarray, sigma: float = 1.0) -> np.ndarray:
    if sigma <= 0:
        return np.asarray(x, dtype=F32)
    return gaussian_filter(np.asarray(x, dtype=F32), sigma=sigma, mode="constant").astype(F32)


def norm01(x: np.ndarray, keep: np.ndarray, hi_pct: float = 99.0) -> np.ndarray:
    values = np.asarray(x)[np.asarray(keep, dtype=bool)]
    if values.size == 0:
        return np.zeros_like(x, dtype=F32)
    hi = float(np.percentile(values, hi_pct))
    if not math.isfinite(hi) or hi <= 0:
        return np.zeros_like(x, dtype=F32)
    return np.clip(np.asarray(x, dtype=F32) / F32(hi), 0.0, 1.0).astype(F32)


def empirical_percentile_surface(x: np.ndarray, keep: np.ndarray) -> np.ndarray:
    """Tie-aware empirical CDF on the kept cells, computed in memory-bounded chunks."""
    x = np.asarray(x, dtype=F32)
    keep = np.asarray(keep, dtype=bool)
    values = x[keep].astype(np.float64, copy=False)
    out = np.zeros(x.shape, dtype=F32)
    if values.size == 0:
        return out
    ordered = np.sort(values, kind="mergesort")
    # Query in chunks so two int64 search-result buffers never span the full raster.
    flat_keep = np.flatnonzero(keep.ravel())
    flat_x = x.ravel()
    flat_out = out.ravel()
    chunk = 500_000
    denominator = max(1.0, float(values.size - 1))
    for start in range(0, flat_keep.size, chunk):
        idx = flat_keep[start:start + chunk]
        q = flat_x[idx].astype(np.float64, copy=False)
        left = np.searchsorted(ordered, q, side="left")
        right = np.searchsorted(ordered, q, side="right")
        flat_out[idx] = ((left + right - 1.0) / (2.0 * denominator)).astype(F32)
    out[~keep] = 0.0
    return out


def geometric_mean(terms: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("geometric-mean weights must sum to a positive value")
    first = next(iter(terms.values()))
    acc = np.zeros_like(first, dtype=F32)
    for name, weight in weights.items():
        term = np.clip(np.asarray(terms[name], dtype=F32), 0.0, 1.0)
        adjusted = F32(GEOMETRIC_MEAN_FLOOR) + F32(1.0 - GEOMETRIC_MEAN_FLOOR) * term
        acc += F32(weight / total) * np.log(adjusted)
    return np.exp(acc).astype(F32)


LIDAR_BANDS = (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
    "upface_max", "cross_max", "relief", "coh100", "strike", "valid",
)
LIDAR_QUANT = {
    "ex_max": (1.5, "sqrt"), "ex_mean": (0.3, "sqrt"), "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"), "lappos_max": (0.05, "sqrt"),
    "downface_max": (1.0, "sqrt"), "upface_max": (1.0, "sqrt"),
    "cross_max": (1.0, "sqrt"), "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"), "strike": (180.0, "linear"), "valid": (1.0, "linear"),
}


def decode_lidar(band_u8: np.ndarray, name: str) -> np.ndarray:
    xmax, transform = LIDAR_QUANT[name]
    q = np.asarray(band_u8, dtype=F32)
    fraction = np.clip((q - F32(1.0)) / F32(254.0), 0.0, 1.0)
    return (F32(xmax) * fraction**2 if transform == "sqrt" else F32(xmax) * fraction).astype(F32)


def _lidar_band(path: str | Path, index: int) -> np.ndarray:
    # Match H42's producer-aware decode: use the raw uint8 quantization exactly and let
    # the explicit `valid` band, not TIFF nodata metadata, determine coverage.
    import rasterio

    with rasterio.open(path) as src:
        return src.read(index).astype(F32)


def _lidar_norm(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    values = np.asarray(x)[valid]
    if values.size == 0:
        return np.zeros_like(x, dtype=F32)
    hi = float(np.percentile(values, 99.5))
    if not math.isfinite(hi) or hi <= 0:
        return np.zeros_like(x, dtype=F32)
    return np.clip(np.asarray(x, dtype=F32) / F32(hi), 0.0, 1.0).astype(F32)


def load_lidar_evidence(path: str | Path) -> tuple[np.ndarray, dict]:
    """Recreate the sibling H42 LiDAR scarp evidence from the pinned 12-band uint8 raster."""
    valid_raw = _lidar_band(path, LIDAR_BANDS.index("valid") + 1)
    valid = valid_raw > 0
    step = _lidar_norm(decode_lidar(_lidar_band(path, LIDAR_BANDS.index("step_max") + 1), "step_max"), valid)
    ex = _lidar_norm(decode_lidar(_lidar_band(path, LIDAR_BANDS.index("ex_max") + 1), "ex_max"), valid)
    step_pair = np.maximum(step, ex)
    del step, ex
    lapneg = _lidar_norm(decode_lidar(_lidar_band(path, LIDAR_BANDS.index("lapneg_max") + 1), "lapneg_max"), valid)
    lappos = _lidar_norm(decode_lidar(_lidar_band(path, LIDAR_BANDS.index("lappos_max") + 1), "lappos_max"), valid)
    break_pair = np.minimum(lapneg, lappos)
    del lapneg, lappos
    coherence = np.clip(decode_lidar(_lidar_band(path, LIDAR_BANDS.index("coh100") + 1), "coh100"), 0.0, 1.0)
    evidence = (F32(0.5) * step_pair + F32(0.5) * break_pair) * coherence
    evidence[~valid] = 0.0
    np.clip(evidence, 0.0, 1.0, out=evidence)
    return evidence.astype(F32), {"lidar_valid_cells": int(valid.sum()), "evidence_max": float(evidence.max(initial=0.0))}


def greedy_pack(score: np.ndarray, allowed: np.ndarray, min_sep: float = 4.0,
                budget: int = 40_000, candidate_cap: int = 2_000_000) -> np.ndarray:
    """Stable greedy disk packing, matching the H42 proxy's separation/budget rule."""
    score = np.asarray(score, dtype=F32)
    allowed = np.asarray(allowed, dtype=bool)
    if score.shape != allowed.shape:
        raise ValueError("score and allowed must have the same shape")
    selected = np.zeros(score.shape, dtype=bool)
    if budget <= 0:
        return selected
    flat_score = score.ravel()
    cells = np.flatnonzero(allowed.ravel() & np.isfinite(flat_score))
    if cells.size == 0:
        return selected
    order = np.argsort(-flat_score[cells], kind="stable")
    if order.size > candidate_cap:
        order = order[:candidate_cap]
    cells = cells[order]
    height, width = score.shape
    blocked = np.zeros(score.shape, dtype=bool)
    radius = int(math.ceil(min_sep))
    yy, xx = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    disk = (yy * yy + xx * xx) <= min_sep**2
    count = 0
    for flat_idx in cells:
        row, col = divmod(int(flat_idx), width)
        if blocked[row, col]:
            continue
        selected[row, col] = True
        count += 1
        r0, r1 = max(0, row - radius), min(height, row + radius + 1)
        c0, c1 = max(0, col - radius), min(width, col + radius + 1)
        dr0, dc0 = r0 - (row - radius), c0 - (col - radius)
        sub = blocked[r0:r1, c0:c1]
        sub |= disk[dr0:dr0 + sub.shape[0], dc0:dc0 + sub.shape[1]]
        if count >= budget:
            break
    return selected
