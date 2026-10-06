"""Published H42 feature surfaces, reimplemented for independent local reproduction."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio

from .density import geometric_mean, norm01, smooth
from .io import ROOT, read_band
from .scarp import load_evidence

SCARP_PATH = "data/external/lidar_scarp_features_u8.tif"


def build_h42_surfaces(root: Path = ROOT) -> dict[str, np.ndarray]:
    """Recreate SA, SB and SH exactly as declared in GEMSDOE41's holdout script."""
    with rasterio.open(root / "data/sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    feature_path = root / "data/training_features.tif"
    slope = norm01(smooth(read_band(feature_path, 19), 1.0), footprint)
    detrended = norm01(smooth(read_band(feature_path, 12), 1.0), footprint)
    magnetic_hg = norm01(smooth(read_band(feature_path, 3), 1.0), footprint)
    scarp, _ = load_evidence(root / SCARP_PATH)
    scarp = norm01(smooth(scarp, 1.0), footprint)

    det_up = np.clip(detrended, 0.0, 1.0)
    surfaces = {
        "SA_slope_scarp": geometric_mean(
            {"s": slope, "k": scarp}, {"s": 0.6, "k": 0.4}
        ),
        "SB_slope_scarp_tmi": geometric_mean(
            {"s": slope, "k": scarp, "t": magnetic_hg},
            {"s": 0.5, "k": 0.3, "t": 0.2},
        ),
        "SH_basin_strong": geometric_mean(
            {"f": (slope**0.5) * ((1.0 - det_up) ** 1.5), "k": scarp, "t": magnetic_hg},
            {"f": 0.55, "k": 0.25, "t": 0.20},
        ),
    }
    return surfaces
