"""Distance-weighted Tversky index used by the local catalogue-transfer proxy.

Transcribed from DrivenData's public GEMS problem description (alpha=.2, beta=.8,
R=300 m = three 100 m cells). The local experiment scores the *published* catalogue in
held-out geographic blocks, so this is a geometry-ranking proxy, not the private test score.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
EPS = 1e-12
_OFFSETS = tuple(
    (dy, dx, max(1.0 - float(np.hypot(dy, dx)) / RADIUS_PX, 0.0))
    for dy in range(-3, 4)
    for dx in range(-3, 4)
    if float(np.hypot(dy, dx)) <= RADIUS_PX
)


def dti(prediction: np.ndarray, truth: np.ndarray, footprint: np.ndarray | None = None) -> dict:
    """Compute official DTI terms on an optional evaluation mask.

    For this proxy, `truth` is the public fault raster and `footprint` is exactly one
    held-out fold's interior. The routine intentionally does not use an official-known
    fault exclusion mask, matching the prior H42 proxy protocol.
    """
    pred = np.asarray(prediction, dtype=np.float64)
    tru = np.asarray(truth)
    if pred.shape != tru.shape:
        raise ValueError("prediction and truth must have identical shapes")
    active = np.ones(pred.shape, dtype=bool) if footprint is None else np.asarray(footprint, dtype=bool)
    if active.shape != pred.shape:
        raise ValueError("footprint and prediction must have identical shapes")
    p = np.where(active & np.isfinite(pred), np.clip(pred, 0.0, 1.0), 0.0)
    g = active & (tru > 0)
    ys, xs = np.nonzero(g)
    n_truth = int(ys.size)
    if n_truth == 0:
        return {"tp": 0.0, "fp": float(p.sum()), "fn": 0.0,
                "n_truth": 0, "mass": float(p.sum()), "dti": 0.0}

    best = np.zeros(n_truth, dtype=np.float64)
    height, width = p.shape
    for dy, dx, weight in _OFFSETS:
        ny, nx = ys + dy, xs + dx
        valid = (ny >= 0) & (ny < height) & (nx >= 0) & (nx < width)
        if valid.any():
            best[valid] = np.maximum(best[valid], p[ny[valid], nx[valid]] * weight)
    tp = float(best.sum(dtype=np.float64))

    distance = distance_transform_edt(~g)
    own_kernel = np.maximum(1.0 - distance / RADIUS_PX, 0.0)
    fp = float((p * (1.0 - np.minimum(own_kernel, 1.0))).sum(dtype=np.float64))
    fn = float(n_truth) - tp
    denom = tp + ALPHA * fp + BETA * fn + EPS
    return {"tp": tp, "fp": fp, "fn": fn, "n_truth": n_truth,
            "mass": float(p.sum(dtype=np.float64)), "dti": float(tp / denom)}


def dti_bruteforce(prediction: np.ndarray, truth: np.ndarray,
                   footprint: np.ndarray | None = None) -> dict:
    """Small-array direct formula, retained solely as an independent test oracle."""
    pred = np.asarray(prediction, dtype=np.float64)
    tru = np.asarray(truth)
    active = np.ones(pred.shape, dtype=bool) if footprint is None else np.asarray(footprint, dtype=bool)
    p = np.where(active & np.isfinite(pred), np.clip(pred, 0.0, 1.0), 0.0)
    g = active & (tru > 0)
    gy, gx = np.nonzero(g)
    py, px = np.nonzero(p > 0)
    if gy.size == 0:
        return {"tp": 0.0, "fp": float(p.sum()), "fn": 0.0,
                "n_truth": 0, "mass": float(p.sum()), "dti": 0.0}
    tp = 0.0
    for y, x in zip(gy, gx):
        d = np.hypot(py - y, px - x)
        tp += float(np.max(p[py, px] * np.maximum(1.0 - d / RADIUS_PX, 0.0))) if px.size else 0.0
    fp = 0.0
    for y, x in zip(py, px):
        d = np.hypot(gy - y, gx - x)
        k = float(np.max(np.maximum(1.0 - d / RADIUS_PX, 0.0)))
        fp += float(p[y, x] * (1.0 - min(k, 1.0)))
    fn = float(gy.size) - tp
    denom = tp + ALPHA * fp + BETA * fn + EPS
    return {"tp": tp, "fp": fp, "fn": fn, "n_truth": int(gy.size),
            "mass": float(p.sum()), "dti": float(tp / denom)}
