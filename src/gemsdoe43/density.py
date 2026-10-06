"""Deterministic score normalization and separated-point emission."""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

F32 = np.float32
EPS_FLOOR = 0.05


def norm01(values: np.ndarray, keep: np.ndarray, high_percentile: float = 99.0) -> np.ndarray:
    """Normalize by a robust high percentile over `keep`; return finite values in [0,1]."""
    values = np.asarray(values, dtype=F32)
    keep = np.asarray(keep, bool)
    if values.shape != keep.shape:
        raise ValueError("values and keep mask must have the same shape")
    valid = keep & np.isfinite(values)
    selected = values[valid]
    if selected.size == 0:
        return np.zeros(values.shape, dtype=F32)
    high = float(np.percentile(selected, high_percentile))
    if not np.isfinite(high) or high <= 0.0:
        return np.zeros(values.shape, dtype=F32)
    out = np.zeros(values.shape, dtype=F32)
    out[valid] = np.clip(values[valid] / F32(high), 0.0, 1.0)
    return out


def smooth(values: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing with the H42 baseline's constant-zero boundary convention."""
    if sigma <= 0.0:
        return np.asarray(values, dtype=F32)
    return gaussian_filter(np.asarray(values, dtype=F32), sigma=sigma, mode="constant").astype(F32)


def geometric_mean(terms: dict[str, np.ndarray], weights: dict[str, float]) -> np.ndarray:
    """Weighted geometric mean with a 0.05 floor (the H42 surface convention)."""
    if not terms or set(terms) != set(weights):
        raise ValueError("terms and weights must have identical nonempty keys")
    total = float(sum(weights.values()))
    if total <= 0.0 or any(w < 0.0 for w in weights.values()):
        raise ValueError("weights must be nonnegative and have positive total")
    shape = next(iter(terms.values())).shape
    log_score = np.zeros(shape, dtype=F32)
    for name, weight in weights.items():
        term = np.asarray(terms[name], dtype=F32)
        if term.shape != shape:
            raise ValueError("geometric-mean terms have different shapes")
        bounded = np.clip(np.where(np.isfinite(term), term, 0.0), 0.0, 1.0)
        log_score += F32(weight / total) * np.log(F32(EPS_FLOOR) + F32(1.0 - EPS_FLOOR) * bounded)
    return np.exp(log_score).astype(F32)


def greedy_pack(
    score: np.ndarray,
    allowed: np.ndarray,
    min_sep: float,
    budget: int,
    candidate_cap: int = 2_000_000,
) -> np.ndarray:
    """Greedily emit the highest-scoring allowed cells at least `min_sep` apart.

    The stable sort and disk-shaped exclusion match the published GEMSDOE41 H42
    implementation (`src/gemsdoe41/density.py::greedy_pack`).
    """
    if min_sep < 0.0 or budget < 0 or candidate_cap <= 0:
        raise ValueError("min_sep/candidate_cap/budget out of range")
    score = np.asarray(score)
    allowed = np.asarray(allowed, bool)
    if score.ndim != 2 or score.shape != allowed.shape:
        raise ValueError("score and allowed must be same-shape 2-D arrays")
    result = np.zeros(score.shape, dtype=bool)
    if budget == 0:
        return result
    flat = np.flatnonzero(allowed.ravel() & np.isfinite(score.ravel()))
    if flat.size == 0:
        return result
    values = score.ravel()[flat]
    order = np.argsort(-values, kind="stable")
    if order.size > candidate_cap:
        order = order[:candidate_cap]
    cells = flat[order]
    height, width = score.shape
    blocked = np.zeros(score.shape, dtype=bool)
    radius = int(np.ceil(min_sep))
    offsets = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    disc = (offsets[0] ** 2 + offsets[1] ** 2) <= min_sep**2
    selected = 0
    for index in cells:
        row, col = divmod(int(index), width)
        if blocked[row, col]:
            continue
        result[row, col] = True
        selected += 1
        r0, r1 = max(0, row - radius), min(height, row + radius + 1)
        c0, c1 = max(0, col - radius), min(width, col + radius + 1)
        sub = blocked[r0:r1, c0:c1]
        dr = r0 - (row - radius)
        dc = c0 - (col - radius)
        sub |= disc[dr:dr + sub.shape[0], dc:dc + sub.shape[1]]
        if selected >= budget:
            break
    return result


def catalogue_distance(catalogue: np.ndarray) -> np.ndarray:
    """Euclidean distance from each grid cell to the nearest catalogue pixel."""
    cat = np.asarray(catalogue, bool)
    if not cat.any():
        return np.full(cat.shape, np.inf, dtype=F32)
    return distance_transform_edt(~cat).astype(F32)
