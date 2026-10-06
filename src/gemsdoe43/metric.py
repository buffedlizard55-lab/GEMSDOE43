"""Distance-weighted Tversky metric used by the GEMS task.

The formulas below transcribe the official problem description. Organizer staff later
confirmed that pixels representing published USGS/INGENIOUS faults are masked from both
the false-positive and other evaluation terms (see research/data_access.md and the
linked staff reply). The catalogue holdout in this repository deliberately uses
`known=None`: held-out published traces are the validation truth in that separate
instrument, not pixels to mask out.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0  # 300 m on the verified 100 m competition grid
EPS = 1e-12

OFFSETS: tuple[tuple[int, int, float], ...] = tuple(
    (dy, dx, max(1.0 - float(np.hypot(dy, dx)) / RADIUS_PX, 0.0))
    for dy in range(-3, 4)
    for dx in range(-3, 4)
    if float(np.hypot(dy, dx)) <= RADIUS_PX
)


def kernel(distance: np.ndarray | float) -> np.ndarray:
    """Triangular distance kernel `max(1 - d/3, 0)` with d measured in cells."""
    return np.maximum(1.0 - np.asarray(distance, dtype=np.float64) / RADIUS_PX, 0.0)


def dti(
    prediction: np.ndarray,
    truth: np.ndarray,
    footprint: np.ndarray | None = None,
    known: np.ndarray | None = None,
    *,
    truth_distance: np.ndarray | None = None,
) -> dict[str, float | int]:
    """Compute weighted TP, FP, FN and DTI.

    Parameters follow the official semantics: nonfinite prediction values contribute zero;
    values are clipped to [0,1]; `known` removes pixels from both prediction mass and truth.
    `truth_distance` is an optional exact cache of distance-to-truth for repeated calls on
    the same mask. It must be computed from the active truth (`footprint & ~known & truth`).
    """
    pred = np.asarray(prediction)
    tru = np.asarray(truth)
    if pred.ndim != 2 or pred.shape != tru.shape:
        raise ValueError("prediction and truth must be same-shape 2-D arrays")
    active = np.ones(pred.shape, dtype=bool) if footprint is None else np.asarray(footprint, bool)
    if active.shape != pred.shape:
        raise ValueError("footprint shape mismatch")
    if known is not None:
        known_mask = np.asarray(known, bool)
        if known_mask.shape != pred.shape:
            raise ValueError("known mask shape mismatch")
        active = active & ~known_mask
    p = np.asarray(pred, dtype=np.float64)
    p = np.where(active & np.isfinite(p), np.clip(p, 0.0, 1.0), 0.0)
    g = active & (tru > 0)
    ys, xs = np.nonzero(g)
    n_truth = int(ys.size)
    if n_truth == 0:
        mass = float(p.sum(dtype=np.float64))
        fp = mass
        denom = ALPHA * fp + EPS
        return {"tp": 0.0, "fp": fp, "fn": 0.0, "n_truth": 0,
                "dti": 0.0, "credit_per_mass": 0.0, "mass": mass}

    # For each truth pixel, find the largest prediction * triangular-kernel product
    # within the three-cell radius. Work over the sparse truth coordinates.
    best = np.zeros(n_truth, dtype=np.float64)
    height, width = p.shape
    for dy, dx, weight in OFFSETS:
        ny = ys + dy
        nx = xs + dx
        inside = (ny >= 0) & (ny < height) & (nx >= 0) & (nx < width)
        if inside.any():
            candidates = np.zeros(n_truth, dtype=np.float64)
            candidates[inside] = p[ny[inside], nx[inside]] * weight
            np.maximum(best, candidates, out=best)
    tp = float(best.sum(dtype=np.float64))

    if truth_distance is None:
        dist = distance_transform_edt(~g)
    else:
        dist = np.asarray(truth_distance)
        if dist.shape != pred.shape:
            raise ValueError("truth_distance shape mismatch")
    py, px = np.nonzero(p > 0.0)
    if py.size:
        own_weight = kernel(dist[py, px])
        fp = float(np.sum(p[py, px] * (1.0 - np.minimum(own_weight, 1.0)), dtype=np.float64))
        mass = float(np.sum(p[py, px], dtype=np.float64))
    else:
        fp = 0.0
        mass = 0.0
    fn = float(n_truth) - tp
    denominator = tp + ALPHA * fp + BETA * fn + EPS
    score = float(tp / denominator) if denominator > 0.0 else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "n_truth": n_truth, "dti": score,
            "credit_per_mass": (tp / mass if mass > 0.0 else 0.0), "mass": mass}


def dti_bruteforce(
    prediction: np.ndarray,
    truth: np.ndarray,
    footprint: np.ndarray | None = None,
    known: np.ndarray | None = None,
) -> dict[str, float | int]:
    """Slow, direct O(|truth| × |prediction|) formula, for small-array tests only."""
    pred = np.asarray(prediction, dtype=np.float64)
    tru = np.asarray(truth)
    if pred.ndim != 2 or pred.shape != tru.shape:
        raise ValueError("prediction and truth must be same-shape 2-D arrays")
    active = np.ones(pred.shape, dtype=bool) if footprint is None else np.asarray(footprint, bool).copy()
    if known is not None:
        active &= ~np.asarray(known, bool)
    p = np.where(active & np.isfinite(pred), np.clip(pred, 0.0, 1.0), 0.0)
    g = active & (tru > 0)
    gy, gx = np.nonzero(g)
    py, px = np.nonzero(p > 0.0)
    n_truth = int(gy.size)
    if n_truth == 0:
        mass = float(p.sum())
        return {"tp": 0.0, "fp": mass, "fn": 0.0, "n_truth": 0, "dti": 0.0,
                "credit_per_mass": 0.0, "mass": mass}
    tp = 0.0
    for yy, xx in zip(gy, gx):
        distances = np.hypot(py - yy, px - xx)
        weights = np.maximum(1.0 - distances / RADIUS_PX, 0.0)
        tp += float(np.max(p[py, px] * weights)) if py.size else 0.0
    fp = 0.0
    for yy, xx in zip(py, px):
        distances = np.hypot(gy - yy, gx - xx)
        best = float(np.max(np.maximum(1.0 - distances / RADIUS_PX, 0.0)))
        fp += float(p[yy, xx] * (1.0 - best))
    fn = float(n_truth) - tp
    denom = tp + ALPHA * fp + BETA * fn
    mass = float(p[py, px].sum()) if py.size else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "n_truth": n_truth,
            "dti": tp / denom if denom else 0.0,
            "credit_per_mass": tp / mass if mass else 0.0, "mass": mass}
