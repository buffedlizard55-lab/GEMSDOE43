"""G43-CG01: multi-scale magnetic–gravity structural cross-gradient concordance.

Frozen operator (registered in registry/experiment.json before its holdout score was
read): use the reduced-to-pole magnetic field and isostatic gravity anomaly; smooth at
2, 4 and 8 pixels; compute 2-D gradient vectors; normalize each gradient magnitude by
its 99th percentile on valid study-area cells; multiply the geometric mean of the two
strengths by absolute directional cosine; take the median of the three scale responses.
Thus a high score requires two appreciable, co-located gradient vectors whose normals
are aligned (parallel or antiparallel) at at least two scales. No labels, catalogue mask,
LiDAR scarp layer, leaderboard data, or prior submission is read here.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import gaussian_filter

from .density import norm01
from .io import DATA, ROOT, read_named_band

SCALES_PX = (2.0, 4.0, 8.0)
NORMALIZATION_PERCENTILE = 99.0
MAGNETIC_BAND = "rtp"
GRAVITY_BAND = "iso_grav_anom"


def _masked_gaussian(values: np.ndarray, valid: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing that does not invent an edge at a nodata/footprint boundary."""
    weights = np.asarray(valid, dtype=np.float32)
    numerator = gaussian_filter(
        np.where(valid, values, 0.0).astype(np.float32), sigma=sigma, mode="nearest"
    )
    denominator = gaussian_filter(weights, sigma=sigma, mode="nearest")
    out = np.zeros(values.shape, dtype=np.float32)
    np.divide(numerator, denominator, out=out, where=denominator > 1e-6)
    return out


def cross_gradient_score(
    magnetic: np.ndarray,
    gravity: np.ndarray,
    valid: np.ndarray,
    scales_px: tuple[float, ...] = SCALES_PX,
    normalization_percentile: float = NORMALIZATION_PERCENTILE,
) -> np.ndarray:
    """Return a finite [0,1] score for multi-scale co-located edge concordance."""
    magnetic = np.asarray(magnetic, dtype=np.float32)
    gravity = np.asarray(gravity, dtype=np.float32)
    valid = np.asarray(valid, dtype=bool)
    if magnetic.ndim != 2 or magnetic.shape != gravity.shape or magnetic.shape != valid.shape:
        raise ValueError("magnetic, gravity and valid must be same-shape 2-D arrays")
    valid = valid & np.isfinite(magnetic) & np.isfinite(gravity)
    if not valid.any():
        return np.zeros(magnetic.shape, dtype=np.float32)
    responses = []
    for sigma in scales_px:
        if sigma <= 0.0:
            raise ValueError("all smoothing scales must be positive")
        mag_s = _masked_gaussian(magnetic, valid, sigma)
        grav_s = _masked_gaussian(gravity, valid, sigma)
        mag_y, mag_x = np.gradient(mag_s)
        grav_y, grav_x = np.gradient(grav_s)
        mag_amp = np.hypot(mag_x, mag_y)
        grav_amp = np.hypot(grav_x, grav_y)
        mag_strength = norm01(mag_amp, valid, normalization_percentile)
        grav_strength = norm01(grav_amp, valid, normalization_percentile)
        denominator = mag_amp * grav_amp
        alignment = np.zeros(magnetic.shape, dtype=np.float32)
        usable = valid & (denominator > 1e-12)
        dot = mag_x * grav_x + mag_y * grav_y
        alignment[usable] = np.clip(np.abs(dot[usable]) / denominator[usable], 0.0, 1.0)
        response = np.sqrt(mag_strength * grav_strength) * alignment
        response[~valid] = 0.0
        responses.append(response.astype(np.float32, copy=False))
        del mag_s, grav_s, mag_y, mag_x, grav_y, grav_x, mag_amp, grav_amp
        del mag_strength, grav_strength, denominator, alignment, dot
    stacked = np.stack(responses, axis=0)
    score = np.median(stacked, axis=0).astype(np.float32)
    score[~valid] = 0.0
    np.clip(score, 0.0, 1.0, out=score)
    return score


def build_candidate_score(root: Path = ROOT) -> tuple[np.ndarray, np.ndarray]:
    """Load only the preregistered competition bands and build CG01's score surface."""
    features = root / "data/training_features.tif"
    magnetic, mag_valid = read_named_band(features, MAGNETIC_BAND)
    gravity, grav_valid = read_named_band(features, GRAVITY_BAND)
    with rasterio.open(root / "data/sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    valid = footprint & mag_valid & grav_valid
    score = cross_gradient_score(magnetic, gravity, valid)
    return score, valid
