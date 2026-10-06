"""Decode the owner-mirrored 12-band LiDAR scarp product for H42 reproduction only.

The producer description and band quantization are preserved in GEMSDOE24's public
`src/gems41/lidar.py` and data manifest. This module reimplements only the evidence
field required by the published H42 holdout. It is not an input to G43-CG01.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

F32 = np.float32
BANDS = (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
    "upface_max", "cross_max", "relief", "coh100", "strike", "valid",
)
QUANTIZATION = {
    "ex_max": (1.5, "sqrt"),
    "ex_mean": (0.3, "sqrt"),
    "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"),
    "lappos_max": (0.05, "sqrt"),
    "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"),
    "cross_max": (1.0, "sqrt"),
    "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"),
    "strike": (180.0, "linear"),
    "valid": (1.0, "linear"),
}


def decode(values: np.ndarray, name: str) -> np.ndarray:
    """Invert `q = 1 + round(254 * t(clip(x/xmax,0,1)))` quantization."""
    if name not in QUANTIZATION:
        raise KeyError(name)
    maximum, transfer = QUANTIZATION[name]
    q = np.asarray(values, dtype=F32)
    fraction = np.clip((q - F32(1.0)) / F32(254.0), F32(0.0), F32(1.0))
    return (F32(maximum) * fraction**2) if transfer == "sqrt" else F32(maximum) * fraction


def _read(path: Path, band: int) -> np.ndarray:
    with rasterio.open(path) as src:
        if src.count != len(BANDS):
            raise ValueError(f"expected 12 scarp bands, found {src.count}")
        return src.read(band)


def _norm99_5(values: np.ndarray, valid: np.ndarray) -> np.ndarray:
    population = values[valid]
    if population.size == 0:
        return np.zeros(values.shape, dtype=F32)
    high = float(np.percentile(population, 99.5))
    if high <= 0.0:
        return np.zeros(values.shape, dtype=F32)
    return np.clip(values / F32(high), F32(0.0), F32(1.0)).astype(F32)


def load_evidence(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return `(evidence, valid_mask)` following the published H42 decoder exactly."""
    valid = _read(path, BANDS.index("valid") + 1) > 0

    step = _norm99_5(decode(_read(path, BANDS.index("step_max") + 1), "step_max"), valid)
    ex = _norm99_5(decode(_read(path, BANDS.index("ex_max") + 1), "ex_max"), valid)
    step = np.maximum(step, ex)
    del ex

    lap_negative = _norm99_5(
        decode(_read(path, BANDS.index("lapneg_max") + 1), "lapneg_max"), valid
    )
    lap_positive = _norm99_5(
        decode(_read(path, BANDS.index("lappos_max") + 1), "lappos_max"), valid
    )
    break_pair = np.minimum(lap_negative, lap_positive)
    del lap_negative, lap_positive

    coherence = np.clip(decode(_read(path, BANDS.index("coh100") + 1), "coh100"), 0.0, 1.0)
    evidence = (F32(0.5) * step + F32(0.5) * break_pair) * coherence
    evidence[~valid] = 0.0
    np.clip(evidence, 0.0, 1.0, out=evidence)
    return evidence.astype(F32, copy=False), valid
