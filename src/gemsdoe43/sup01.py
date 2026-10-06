"""G43-SUP01: per-fold supervised fault ranker (frozen in round-2b amendment).

Features (21): the 19 competition bands in band order, the LiDAR scarp evidence
(0-imputed where invalid), and a scarp-validity flag. No coordinates, no labels
outside the training region. The classifier's probability ranks cells for the
existing fixed-separation packing; ranks only, so no calibration step is used.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from sklearn.ensemble import HistGradientBoostingClassifier

from .io import ROOT, read_band_with_mask
from .scarp import load_evidence

HGB_PARAMS = {
    "max_iter": 200,
    "learning_rate": 0.06,
    "max_leaf_nodes": 63,
    "min_samples_leaf": 200,
    "l2_regularization": 1.0,
    "class_weight": "balanced",
    "early_stopping": True,
    "validation_fraction": 0.1,
    "n_iter_no_change": 20,
    "random_state": 20261006,
}


def load_feature_stack(root: Path = ROOT) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Return (flat float32 stack (n_cells, 21), bands_valid mask, feature names)."""
    feature_path = root / "data/training_features.tif"
    with rasterio.open(feature_path) as src:
        count = src.count
        names = [src.tags(index + 1).get("band_name", f"band_{index + 1}")
                 for index in range(count)]
        height, width = src.height, src.width
    if count != 19:
        raise ValueError(f"expected 19 feature bands, found {count}")
    n_cells = height * width
    stack = np.zeros((n_cells, count + 2), dtype=np.float32)
    bands_valid = np.ones((height, width), dtype=bool)
    for index in range(count):
        arr, valid = read_band_with_mask(feature_path, index + 1)
        stack[:, index] = arr.ravel()
        bands_valid &= valid
    scarp, scarp_valid = load_evidence(root / "data/external/lidar_scarp_features_u8.tif")
    if scarp.shape != (height, width):
        raise ValueError("scarp grid does not match the feature grid")
    stack[:, count] = np.where(scarp_valid, scarp, 0.0).ravel()
    stack[:, count + 1] = scarp_valid.ravel().astype(np.float32)
    names = names + ["scarp_evidence", "scarp_valid"]
    return stack, bands_valid, names


def train_predict_proba(
    stack: np.ndarray,
    train_flat: np.ndarray,
    train_labels: np.ndarray,
    pred_flat: np.ndarray,
) -> tuple[np.ndarray, dict]:
    """Fit the frozen HGB on training cells; return P(truth) for prediction cells."""
    clf = HistGradientBoostingClassifier(**HGB_PARAMS)
    clf.fit(stack[train_flat], train_labels.astype(np.int8))
    proba = clf.predict_proba(stack[pred_flat])[:, 1].astype(np.float32)
    info = {
        "n_train": int(train_flat.size),
        "n_train_positive": int(np.count_nonzero(train_labels)),
        "n_iter": int(getattr(clf, "n_iter_", -1)),
        "params": {key: getattr(clf, key) for key in HGB_PARAMS},
    }
    return proba, info


def fit_predict_in_sample(
    matrix: np.ndarray, labels: np.ndarray
) -> tuple[np.ndarray, dict]:
    """Fit the frozen HGB on a materialized matrix; predict the same rows.

    Same hyperparameters as train_predict_proba; used by the full-footprint
    build so the 1 GB flat stack can be released before fitting (3.9 GB sandbox).
    """
    clf = HistGradientBoostingClassifier(**HGB_PARAMS)
    clf.fit(np.ascontiguousarray(matrix), labels.astype(np.int8))
    proba = clf.predict_proba(np.ascontiguousarray(matrix))[:, 1].astype(np.float32)
    info = {
        "n_train": int(matrix.shape[0]),
        "n_train_positive": int(np.count_nonzero(labels)),
        "n_iter": int(getattr(clf, "n_iter_", -1)),
        "params": {key: getattr(clf, key) for key in HGB_PARAMS},
    }
    return proba, info
