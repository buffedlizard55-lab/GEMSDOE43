"""Run the source-gated H46-B SGMC auxiliary-contact experiment against H42."""
from __future__ import annotations

import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from .experiment import (
    PRIOR_H42_FOLDS,
    PRIOR_H42_MEAN,
    _assert_aligned,
    _baseline_surface,
    _fold_ids,
    _load_labels,
    _read_footprint,
    sha256,
)
from .geology import contact_contrast, load_sgmc_unit_raster, source_viability_gates
from .metric import dti
from .surface import empirical_percentile_surface, geometric_mean, greedy_pack, read_band, smooth

F32 = np.float32
EXPERIMENT_ID = "GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006"
SUBMISSION_NAME = "GEMSDOE43-H46B-SGMC-H42CONTACT-40K-20261006"
SGMC_PINS = {
    "CA": (24_977_406, "78765ba4428df9f25a84f86e0b2529bd0508fc8a2cf65d2f41a830e82bccfd58"),
    "NV": (69_056_094, "3b333ac025e59aae7f0d827db45ba32c425cf867eb341561a788af1de186b76b"),
    "tables": (1_573_709, "8859dd1f00ec6ec3d397634dc86fa288e440b432aad8a98a5fb0c7f9b6bc0bde"),
}
SGMC_URLS = {
    "CA": "https://mrdata.usgs.gov/geology/state/shp/CA.zip",
    "NV": "https://mrdata.usgs.gov/geology/state/shp/NV.zip",
    "tables": "https://www.sciencebase.gov/catalog/file/get/5888bf4fe4b05ccb964bab9d?name=USGS_SGMC_Tables_CSV.zip",
}


def _verify_sgmc_archives(archives: dict[str, Path]) -> dict:
    receipts = {}
    for key, path in archives.items():
        path = Path(path)
        if key not in SGMC_PINS:
            raise ValueError(f"Unexpected SGMC source key: {key}")
        expected_bytes, expected_sha = SGMC_PINS[key]
        if not path.is_file():
            raise FileNotFoundError(f"Missing SGMC {key} archive: {path}")
        actual_bytes = path.stat().st_size
        actual_sha = sha256(path)
        if actual_bytes != expected_bytes or actual_sha != expected_sha:
            raise ValueError(
                f"Pinned SGMC {key} archive mismatch: bytes={actual_bytes}, sha256={actual_sha}; "
                f"expected bytes={expected_bytes}, sha256={expected_sha}"
            )
        receipts[key] = {
            "path": str(path), "bytes": actual_bytes, "sha256": actual_sha,
            "official_url": SGMC_URLS[key], "verification": "exact byte count and SHA-256 match",
        }
    missing = sorted(set(SGMC_PINS) - set(receipts))
    if missing:
        raise ValueError(f"Missing required pinned SGMC archives: {missing}")
    return receipts


def _h46b_surface(
    *,
    features_path: Path,
    baseline_surface: np.ndarray,
    unit_raster,
    footprint: np.ndarray,
) -> tuple[np.ndarray, dict]:
    contrast, contrast_report = contact_contrast(unit_raster.unit_id, unit_raster, footprint)
    source_gates = source_viability_gates(contrast_report)
    if not all(source_gates.values()):
        raise RuntimeError(f"H46-B preregistered SGMC source gate failed: {source_gates}")

    tmi_hg_smoothed = smooth(read_band(features_path, 3), 1.0)
    tmi_rank = empirical_percentile_surface(tmi_hg_smoothed, footprint)
    auxiliary = (contrast * tmi_rank).astype(F32)
    auxiliary[~footprint] = 0.0
    candidate = geometric_mean(
        {"h42_incumbent": baseline_surface, "sgmc_contact_tmi": auxiliary},
        {"h42_incumbent": 0.75, "sgmc_contact_tmi": 0.25},
    )
    candidate[~footprint] = 0.0
    if not np.isfinite(candidate[footprint]).all() or np.any((candidate[footprint] < 0) | (candidate[footprint] > 1)):
        raise ValueError("H46-B candidate surface is not finite and bounded on the footprint")
    if np.any(candidate[~footprint] != 0):
        raise ValueError("H46-B candidate surface is nonzero outside the footprint")
    report = {
        "arm": "H46-B SGMC lithology/age contact x TMI evidence, combined with H42 incumbent",
        "fixed_formula": "geometric_mean(H42 incumbent^0.75, (contact_contrast * empirical_percentile(smoothed TMI-HG))^0.25); existing 0.05 geometric-mean floor",
        "source_viability_gates": source_gates,
        "contact_contrast_audit": contrast_report,
        "tmi_feature": {"band": 3, "description": "TMI horizontal gradient", "gaussian_sigma_pixels": 1.0,
                        "rank": "empirical percentile within finite footprint"},
        "auxiliary_surface": {"positive_cells": int(np.count_nonzero(auxiliary > 0)),
                              "max": float(auxiliary.max(initial=0.0))},
        "candidate_surface": {"finite_inside": bool(np.isfinite(candidate[footprint]).all()),
                              "inside_min": float(candidate[footprint].min(initial=0.0)),
                              "inside_max": float(candidate[footprint].max(initial=0.0)),
                              "positive_cells": int(np.count_nonzero(candidate[footprint] > 0)),
                              "outside_nonzero_cells": int(np.count_nonzero(candidate[~footprint]))},
    }
    return candidate.astype(F32), report


def _score_folds(
    baseline_surface: np.ndarray,
    candidate_surface: np.ndarray,
    labels: np.ndarray,
    footprint: np.ndarray,
) -> dict:
    if not (baseline_surface.shape == candidate_surface.shape == labels.shape == footprint.shape):
        raise ValueError("All experiment arrays must have identical shapes")
    fold_ids = _fold_ids(labels.shape)
    folds = []
    for fold in range(4):
        started = time.time()
        held = (fold_ids == fold) & footprint
        forbidden = distance_transform_edt(~held) <= 3.0
        training = labels & ~forbidden
        evaluation = held & (distance_transform_edt(held) > 3.0)
        distance_from_training = distance_transform_edt(~training).astype(F32)
        allowed = evaluation & (distance_from_training > 2.0)
        allowed_count = int(allowed.sum())
        if allowed_count < 40_000:
            raise RuntimeError(f"Fold {fold} has only {allowed_count} allowed cells, below 40,000")

        arms = {}
        for name, surface in (("incumbent", baseline_surface), ("h46b", candidate_surface)):
            prediction = greedy_pack(surface, allowed, min_sep=4.0, budget=40_000,
                                     candidate_cap=2_000_000)
            if int(prediction.sum()) != 40_000:
                raise RuntimeError(f"Fold {fold} {name} packing emitted {int(prediction.sum())}, expected 40,000")
            result = dti(prediction.astype(F32), labels, footprint=evaluation)
            arms[name] = {
                "prediction_pixels": int(prediction.sum()),
                "mass": round(float(result["mass"]), 4),
                "truth_pixels": int(result["n_truth"]),
                "tp_weighted": round(float(result["tp"]), 5),
                "fp_weighted": round(float(result["fp"]), 5),
                "dti": round(float(result["dti"]), 6),
            }
            del prediction
        folds.append({
            "fold": fold,
            "evaluation_cells": int(evaluation.sum()),
            "held_cells": int(held.sum()),
            "training_label_pixels": int(training.sum()),
            "allowed_cells": allowed_count,
            "arms": arms,
            "seconds": round(time.time() - started, 2),
        })
        del held, forbidden, training, evaluation, distance_from_training, allowed

    incumbent = [item["arms"]["incumbent"]["dti"] for item in folds]
    candidate = [item["arms"]["h46b"]["dti"] for item in folds]
    deltas = [round(new - old, 6) for old, new in zip(incumbent, candidate)]
    mean_incumbent = float(np.mean(incumbent))
    mean_candidate = float(np.mean(candidate))
    prior_errors = [round(actual - prior, 6) for actual, prior in zip(incumbent, PRIOR_H42_FOLDS)]
    reproduced = bool(max(abs(value) for value in prior_errors) <= 0.00001)
    mean_delta = mean_candidate - mean_incumbent
    wins = int(sum(delta > 0 for delta in deltas))
    gate = bool(reproduced and mean_delta >= 0.005 and wins >= 3 and min(deltas) >= -0.010)
    return {
        "design": "20 km four-colour geographic blocks; equal 40,000 binary mass/fold; 400 m packing; 300 m fold boundary and two-pixel training-trace guard",
        "fold_formula": "((row//200) + 2*(col//200)) % 4",
        "labels_used_only_for": "fold assignment, training-trace emission guard, and public-catalogue proxy scoring; H42 and H46-B surfaces are built before labels are loaded",
        "score_interpretation": "Public-catalogue spatial-transfer proxy only; not private-set validation or a DrivenData leaderboard score.",
        "promotion_gate": {
            "baseline_must_reproduce_prior_h42_each_fold_within_1e-5": reproduced,
            "same_run_mean_delta_at_least_0_005": mean_delta >= 0.005,
            "h46b_wins_at_least_3_of_4_folds": wins >= 3,
            "no_fold_more_than_0_010_worse": min(deltas) >= -0.010,
            "gate_passed": gate,
            "submission_slot_authorized": False,
            "reason": "A catalogue-transfer proxy is not private-set validation; no submission slot is automatically authorized.",
        },
        "incumbent_prior_reference": {
            "mean_dti": PRIOR_H42_MEAN,
            "fold_dti": PRIOR_H42_FOLDS,
            "same_run_mean_dti": round(mean_incumbent, 6),
            "same_run_fold_dti": incumbent,
            "fold_errors_vs_prior": prior_errors,
        },
        "h46b": {
            "mean_dti": round(mean_candidate, 6),
            "fold_dti": candidate,
            "mean_delta_vs_same_run_incumbent": round(mean_delta, 6),
            "fold_deltas": deltas,
            "wins": wins,
        },
        "folds": folds,
    }


def _write_submission(selected: np.ndarray, footprint: np.ndarray, profile: dict,
                      output_path: Path, holdout_gate_passed: bool) -> dict:
    if selected.shape != footprint.shape or np.any(selected & ~footprint):
        raise ValueError("Selected cells must lie inside the official footprint")
    output = np.full(footprint.shape, np.nan, dtype=np.float32)
    output[footprint] = 0.0
    output[selected] = 1.0
    out_profile = profile.copy()
    out_profile.update(driver="GTiff", count=1, dtype="float32", nodata=np.nan,
                       compress="deflate", predictor=3, tiled=True,
                       blockxsize=256, blockysize=256)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(output_path, "w", **out_profile) as dst:
        dst.write(output, 1)
        dst.set_band_description(1, "H46-B SGMC lithology-age contacts x TMI evidence blended with H42; 40k packed cells")
        dst.update_tags(
            submission_name=SUBMISSION_NAME,
            method="H46-B source-registered; SGMC contact/TMI auxiliary evidence blended with the H42-style incumbent",
            source="USGS State Geologic Map Compilation v1.1, DOI 10.5066/F7WH2N65; competition/LiDAR inputs are integrity-pinned owner mirrors",
            holdout_proxy_gate_passed=str(bool(holdout_gate_passed)).lower(),
            validation="Public-catalogue spatial-blocked proxy only; not private-set validation or a leaderboard score",
            predictions="Binary 0/1 on the finite official footprint; NaN nodata outside",
        )
    with rasterio.open(output_path) as out:
        values = out.read(1)
        finite = np.isfinite(values)
        checks = {
            "shape_matches_footprint": out.shape == footprint.shape,
            "single_band": out.count == 1,
            "dtype_float32": out.dtypes[0] == "float32",
            "crs_epsg_32611": out.crs is not None and out.crs.to_epsg() == 32611,
            "inside_cells_finite": bool(finite[footprint].all()),
            "outside_cells_nodata_nan": bool(np.isnan(values[~footprint]).all()),
            "inside_values_in_0_1": bool(((values[footprint] >= 0) & (values[footprint] <= 1)).all()),
            "grid_transform_preserved": tuple(out.transform) == tuple(profile["transform"]),
            "exactly_40000_predictions": int(np.count_nonzero(values[footprint] > 0)) == 40_000,
        }
        if not all(checks.values()):
            raise RuntimeError(f"Submission-format checks failed: {checks}")
        receipt = {
            "path": str(output_path),
            "submission_name": SUBMISSION_NAME,
            "sha256": sha256(output_path),
            "bytes": output_path.stat().st_size,
            "prediction_pixels": int(np.count_nonzero(values[footprint] > 0)),
            "footprint_cells": int(footprint.sum()),
            "checks": checks,
            "grid": {
                "height": out.height,
                "width": out.width,
                "crs": out.crs.to_string(),
                "transform": [float(v) for v in tuple(out.transform)[:6]],
                "nodata": "NaN",
            },
            "holdout_proxy_gate_passed": bool(holdout_gate_passed),
            "private_set_validation": False,
            "leaderboard_score": None,
        }
    return receipt


def run_experiment(
    *,
    features_path: Path,
    labels_path: Path,
    template_path: Path,
    lidar_path: Path,
    ca_zip_path: Path,
    nv_zip_path: Path,
    tables_zip_path: Path,
    submission_path: Path,
    evidence_dir: Path,
) -> dict:
    """Re-check pinned sources/gates, build label-free surfaces, then score and write H46-B."""
    paths = {
        "features": Path(features_path),
        "labels": Path(labels_path),
        "template": Path(template_path),
        "lidar": Path(lidar_path),
    }
    for name, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing {name} input: {path}")
    archives = {"CA": Path(ca_zip_path), "NV": Path(nv_zip_path), "tables": Path(tables_zip_path)}
    sgmc_receipts = _verify_sgmc_archives(archives)

    # Only the sample-template finite mask/grid is used; template values are not labels or scores.
    footprint, template_info = _read_footprint(paths["template"])
    if template_info["crs"] != "EPSG:32611" or template_info["shape"] != [3730, 3292]:
        raise ValueError(f"Unexpected official template grid: {template_info}")
    baseline, baseline_report = _baseline_surface(paths["features"], paths["lidar"], footprint)
    geology = load_sgmc_unit_raster(
        {"CA": archives["CA"], "NV": archives["NV"]},
        tables_archive=archives["tables"],
        out_shape=footprint.shape,
        transform=template_info["profile"]["transform"],
        target_crs=template_info["profile"]["crs"],
        bounds=template_info["bounds"],
    )
    candidate, candidate_report = _h46b_surface(
        features_path=paths["features"],
        baseline_surface=baseline,
        unit_raster=geology,
        footprint=footprint,
    )
    # Candidate and incumbent surfaces are now complete and source gates are checked;
    # only at this point are the public-catalogue labels opened for the blocked proxy.
    labels = _load_labels(paths["labels"])
    if labels.shape != footprint.shape:
        raise ValueError("Label/footprint shape mismatch")
    grid_receipt = _assert_aligned(paths)
    holdout = _score_folds(baseline, candidate, labels, footprint)

    final_selected = greedy_pack(candidate, footprint, min_sep=4.0, budget=40_000,
                                 candidate_cap=2_000_000)
    if int(final_selected.sum()) != 40_000:
        raise RuntimeError(f"Global H46-B pack emitted {int(final_selected.sum())}, expected 40,000")
    evidence_dir = Path(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    submission = _write_submission(
        final_selected, footprint, template_info["profile"], Path(submission_path),
        bool(holdout["promotion_gate"]["gate_passed"]),
    )

    input_receipts = {
        "competition_features": {"path": str(paths["features"]), "bytes": paths["features"].stat().st_size,
                                 "sha256": sha256(paths["features"]),
                                 "provenance": "integrity-pinned owner-supplied mirror, not organizer-authenticated"},
        "labels": {"path": str(paths["labels"]), "bytes": paths["labels"].stat().st_size,
                   "sha256": sha256(paths["labels"]),
                   "use": "public catalogue only for blocked proxy fold/guard/DTI after candidate construction"},
        "sample_template": {"path": str(paths["template"]), "bytes": paths["template"].stat().st_size,
                            "sha256": sha256(paths["template"]),
                            "use": "finite mask/grid metadata only; sample pixel values not used"},
        "lidar": {"path": str(paths["lidar"]), "bytes": paths["lidar"].stat().st_size,
                  "sha256": sha256(paths["lidar"]),
                  "provenance": "USGS 3DEP-derived 12-band LiDAR scarp product in pinned owner mirror"},
        "sgmc_archives": sgmc_receipts,
        "grid_metadata": grid_receipt,
        "template_footprint": {key: value for key, value in template_info.items() if key != "profile"},
    }
    experiment_report = {
        "schema_version": 1,
        "experiment_id": EXPERIMENT_ID,
        "run_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version,
        "platform": platform.platform(),
        "sources": input_receipts,
        "baseline_surface": baseline_report,
        "candidate_source": {"sgmc_rasterization": geology.report, **candidate_report},
        "holdout": holdout,
        "submission": submission,
        "status": "public-catalogue blocked proxy complete; not private-set validated and not a leaderboard score",
    }
    (evidence_dir / "data_manifest.json").write_text(json.dumps(input_receipts, indent=2, sort_keys=True) + "\n")
    (evidence_dir / "holdout.json").write_text(json.dumps(holdout, indent=2, sort_keys=True) + "\n")
    (evidence_dir / "submission_receipt.json").write_text(json.dumps(submission, indent=2, sort_keys=True) + "\n")
    (evidence_dir / "experiment.json").write_text(json.dumps(experiment_report, indent=2, sort_keys=True) + "\n")
    return experiment_report
