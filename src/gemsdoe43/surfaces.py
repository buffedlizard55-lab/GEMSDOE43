"""Round-2 geological surfaces (frozen in registry/experiment_g43_mclp.json).

G43-MG01: magnetic triple-gradient ridge conjunction. Inputs are the competition
`tmi_hg`, `tmi_vg`, and `rtp` bands only. Each input is smoothed with mask-aware
Gaussian sigma=2 px; the response is the H42-style geometric mean (0.05 floor,
equal weights) of the 99th-percentile-normalized HG strength, |VG| strength, and
RTP gradient-magnitude strength. No labels, catalogue mask, scarp layer,
leaderboard data, or prior submission is read here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from .density import geometric_mean, masked_gaussian, norm01
from .io import ROOT, read_named_band

MG01_SMOOTHING_PX = 2.0
MG01_NORMALIZATION_PERCENTILE = 99.0
MG01_BANDS = ("tmi_hg", "tmi_vg", "rtp")


def triple_gradient_score(
    tmi_hg: np.ndarray,
    tmi_vg: np.ndarray,
    rtp: np.ndarray,
    valid: np.ndarray,
    smoothing_px: float = MG01_SMOOTHING_PX,
    normalization_percentile: float = MG01_NORMALIZATION_PERCENTILE,
) -> np.ndarray:
    """Return a finite [0.05,1] score on valid cells, 0 elsewhere."""
    tmi_hg = np.asarray(tmi_hg, dtype=np.float32)
    tmi_vg = np.asarray(tmi_vg, dtype=np.float32)
    rtp = np.asarray(rtp, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool)
    shapes = {tmi_hg.shape, tmi_vg.shape, rtp.shape, valid.shape}
    if len(shapes) != 1 or tmi_hg.ndim != 2:
        raise ValueError("all inputs must be same-shape 2-D arrays")
    valid = valid & np.isfinite(tmi_hg) & np.isfinite(tmi_vg) & np.isfinite(rtp)
    if not valid.any():
        return np.zeros(tmi_hg.shape, dtype=np.float32)
    hg_s = masked_gaussian(tmi_hg, valid, smoothing_px)
    vg_s = masked_gaussian(tmi_vg, valid, smoothing_px)
    rtp_s = masked_gaussian(rtp, valid, smoothing_px)
    rtp_gy, rtp_gx = np.gradient(rtp_s)
    rtp_grad = np.hypot(rtp_gx, rtp_gy)
    hg_n = norm01(hg_s, valid, normalization_percentile)
    vg_n = norm01(np.abs(vg_s), valid, normalization_percentile)
    rtp_n = norm01(rtp_grad, valid, normalization_percentile)
    score = geometric_mean(
        {"hg": hg_n, "vg": vg_n, "rtp": rtp_n},
        {"hg": 1.0 / 3.0, "vg": 1.0 / 3.0, "rtp": 1.0 / 3.0},
    )
    score[~valid] = 0.0
    np.clip(score, 0.0, 1.0, out=score)
    return score.astype(np.float32, copy=False)


def build_mg01_surface(root: Path = ROOT) -> tuple[np.ndarray, np.ndarray]:
    """Load only the preregistered competition bands and build MG01's score surface."""
    features = root / "data/training_features.tif"
    values: list[np.ndarray] = []
    mask = None
    for band in MG01_BANDS:
        arr, band_valid = read_named_band(features, band)
        values.append(arr)
        mask = band_valid if mask is None else (mask & band_valid)
    assert mask is not None
    with rasterio.open(root / "data/sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    valid = footprint & mask
    score = triple_gradient_score(values[0], values[1], values[2], valid)
    return score, valid
