"""H42 comparator primitives and the stopped H46-A draft; current experiment is H46-B."""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from .geochem import project_to_template, read_ngb_csv, rasterize_local_enrichment
from .metric import dti
from .surface import (
    empirical_percentile_surface,
    geometric_mean,
    greedy_pack,
    load_lidar_evidence,
    norm01,
    read_band,
    smooth,
)

F32 = np.float32
FOLD_FORMULA = "((row//200) + 2*(col//200)) % 4"
PRIOR_H42_FOLDS = [0.242272, 0.247658, 0.255021, 0.258025]
PRIOR_H42_MEAN = 0.250744


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _assert_aligned(paths: dict[str, Path]) -> dict:
    info = {}
    reference = None
    for name, path in paths.items():
        with rasterio.open(path) as ds:
            current = (ds.height, ds.width, ds.crs.to_string() if ds.crs else None,
                       tuple(float(x) for x in tuple(ds.transform)[:6]))
            if reference is None:
                reference = current
            elif current != reference:
                raise ValueError(f"Raster grid mismatch for {name}: {current} != {reference}")
            info[name] = {"shape": [ds.height, ds.width], "crs": ds.crs.to_string() if ds.crs else None,
                          "transform": list(current[3]), "count": ds.count, "dtype": ds.dtypes[0],
                          "bounds": [float(ds.bounds.left), float(ds.bounds.bottom),
                                     float(ds.bounds.right), float(ds.bounds.top)]}
    return info


def _read_footprint(template_path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(template_path) as ds:
        # Use only finite-area membership and the grid. The template's interior sample values
        # are intentionally not read as prediction scores; the source mirror is label-contaminated.
        template_values = ds.read(1)
        footprint = np.isfinite(template_values)
        if ds.nodata is not None and math.isfinite(float(ds.nodata)):
            footprint &= template_values != np.float32(ds.nodata)
        profile = ds.profile.copy()
        shape = (ds.height, ds.width)
        report = {"shape": list(shape), "crs": ds.crs.to_string() if ds.crs else None,
                  "transform": [float(x) for x in tuple(ds.transform)[:6]],
                  "bounds": [float(ds.bounds.left), float(ds.bounds.bottom),
                             float(ds.bounds.right), float(ds.bounds.top)],
                  "finite_footprint_cells": int(footprint.sum()),
                  "template_nodata": None if ds.nodata is None else str(ds.nodata)}
    return footprint, {"profile": profile, **report}


def _load_labels(path: Path) -> np.ndarray:
    labels = read_band(path, 1)
    return labels > 0.5


def _baseline_surface(features_path: Path, lidar_path: Path, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    with rasterio.open(features_path) as src:
        if src.count < 19:
            raise ValueError(f"Expected the 19-band competition raster; found {src.count} bands")
        descriptions = src.descriptions
        if descriptions and descriptions[2] and "tmi_hg" not in descriptions[2].lower():
            raise ValueError(f"Feature band 3 is not labelled tmi_hg: {descriptions[2]!r}")
        if descriptions and descriptions[11] and "det_elev" not in descriptions[11].lower():
            raise ValueError(f"Feature band 12 is not labelled det_elev: {descriptions[11]!r}")
        if descriptions and descriptions[18] and "slope" not in descriptions[18].lower():
            raise ValueError(f"Feature band 19 is not labelled detrended elevation slope: {descriptions[18]!r}")

    slope = norm01(smooth(read_band(features_path, 19), 1.0), footprint)
    detrended = norm01(smooth(read_band(features_path, 12), 1.0), footprint)
    tmi_hg = norm01(smooth(read_band(features_path, 3), 1.0), footprint)
    lidar_raw, lidar_report = load_lidar_evidence(lidar_path)
    scarp = norm01(smooth(lidar_raw, 1.0), footprint)
    detrended = np.clip(detrended, 0.0, 1.0)
    basin = (slope ** F32(0.5)) * ((F32(1.0) - detrended) ** F32(1.5))
    surface = geometric_mean({"basin": basin, "scarp": scarp, "tmi_hg": tmi_hg},
                             {"basin": 0.55, "scarp": 0.25, "tmi_hg": 0.20})
    surface[~footprint] = 0.0
    report = {"arm": "H42 SH_basin_strong|sep4.0|N40000",
              "formula": "GM((slope^0.5*(1-detrended_elevation)^1.5)^0.55, lidar_scarp^0.25, tmi_hg^0.20)",
              "normalization": "sigma=1 pixel constant Gaussian; p99 within finite footprint; H42 geometric-mean floor=.05",
              "lidar": lidar_report,
              "surface_min": float(surface.min(initial=0.0)),
              "surface_max": float(surface.max(initial=0.0))}
    return surface.astype(F32), report


def _candidate_surface(features_path: Path, csv_path: Path, template_path: Path,
                       footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    samples = read_ngb_csv(csv_path)
    all_mapped, all_report = project_to_template(samples.samples, template_path, footprint,
                                                  require_index=False)
    valid_mapped, valid_report = project_to_template(samples.samples, template_path, footprint,
                                                      require_index=True)
    if all_report["samples_in_footprint"] < 1_000:
        raise RuntimeError("H46-A source gate failed: fewer than 1,000 stream sample locations in footprint")
    if valid_report["samples_in_footprint"] < 500:
        raise RuntimeError("H46-A source gate failed: fewer than 500 samples with >=3 clean assays in footprint")
    geo, support, geo_report = rasterize_local_enrichment(valid_mapped, footprint.shape,
                                                          footprint, sigma_px=20.0)
    if not support.any() or not np.any(geo > 0):
        raise RuntimeError("H46-A source gate failed: no supported positive local pathfinder enrichment")
    raw_tmi_hg = smooth(read_band(features_path, 3), 1.0)
    tmi_rank = empirical_percentile_surface(raw_tmi_hg, footprint)
    candidate = np.sqrt(np.clip(geo, 0.0, 1.0) * np.clip(tmi_rank, 0.0, 1.0)).astype(F32)
    candidate[~footprint] = 0.0
    report = {
        "arm": "H46-A NGB pathfinder enrichment x TMI horizontal gradient",
        "fixed_formula": "sqrt(2km-local-mean pathfinder enrichment * empirical-percentile(tmi_hg))",
        "assay_summary": samples.report,
        "stream_sample_coverage": all_report,
        "geochem_eligible_coverage": valid_report,
        "geochemical_raster": geo_report,
        "tmi_rank_min": float(tmi_rank[footprint].min(initial=0.0)),
        "tmi_rank_max": float(tmi_rank[footprint].max(initial=0.0)),
        "candidate_positive_surface_cells": int(np.count_nonzero(candidate > 0)),
        "candidate_surface_max": float(candidate.max(initial=0.0)),
    }
    return candidate, report


def _fold_ids(shape: tuple[int, int]) -> np.ndarray:
    h, w = shape
    row_term = (np.arange(h, dtype=np.int32) // 200)[:, None]
    col_term = (np.arange(w, dtype=np.int32) // 200)[None, :]
    return ((row_term + 2 * col_term) % 4).astype(np.uint8)


def _score_folds(baseline_surface: np.ndarray, candidate_surface: np.ndarray,
                 labels: np.ndarray, footprint: np.ndarray) -> dict:
    if not (baseline_surface.shape == candidate_surface.shape == labels.shape == footprint.shape):
        raise ValueError("All experiment arrays must have identical shapes")
    fold_id = _fold_ids(labels.shape)
    folds = []
    for f in range(4):
        started = time.time()
        held = (fold_id == f) & footprint
        forbidden = distance_transform_edt(~held) <= 3.0
        training = labels & ~forbidden
        evaluation = held & (distance_transform_edt(held) > 3.0)
        d_train = distance_transform_edt(~training).astype(F32)
        allowed = evaluation & (d_train > 2.0)
        if int(allowed.sum()) < 40_000:
            raise RuntimeError(f"Fold {f} has fewer than 40,000 allowed pixels")

        scored = {}
        for name, surface in (("incumbent", baseline_surface), ("h46a", candidate_surface)):
            pred = greedy_pack(surface, allowed, min_sep=4.0, budget=40_000,
                               candidate_cap=2_000_000)
            result = dti(pred.astype(F32), labels, footprint=evaluation)
            scored[name] = {
                "prediction_pixels": int(pred.sum()),
                "mass": round(float(result["mass"]), 4),
                "truth_pixels": int(result["n_truth"]),
                "tp_weighted": round(float(result["tp"]), 5),
                "fp_weighted": round(float(result["fp"]), 5),
                "dti": round(float(result["dti"]), 6),
            }
            del pred
        folds.append({"fold": f, "evaluation_cells": int(evaluation.sum()),
                      "held_cells": int(held.sum()), "training_label_pixels": int(training.sum()),
                      "allowed_cells": int(allowed.sum()), "arms": scored,
                      "seconds": round(time.time() - started, 2)})
        del held, forbidden, training, evaluation, d_train, allowed

    b = [x["arms"]["incumbent"]["dti"] for x in folds]
    c = [x["arms"]["h46a"]["dti"] for x in folds]
    deltas = [round(cv - bv, 6) for bv, cv in zip(b, c)]
    mean_b = float(np.mean(b))
    mean_c = float(np.mean(c))
    prior_fold_errors = [round(x - y, 6) for x, y in zip(b, PRIOR_H42_FOLDS)]
    reproduction_ok = bool(max(abs(x) for x in prior_fold_errors) <= 0.00001)
    gate = bool(
        reproduction_ok
        and mean_c - mean_b >= 0.005
        and sum(d > 0 for d in deltas) >= 3
        and min(deltas) >= -0.010
    )
    return {
        "design": "20 km four-colour geographic blocks; equal 40,000 binary mass/fold; 400 m packing; 300 m fold boundary and two-pixel training-trace guard",
        "fold_formula": FOLD_FORMULA,
        "labels_used_only_for": "fold assignment, training-trace emission guard, and published-catalogue proxy scoring; neither surface reads labels",
        "score_interpretation": "Public-catalogue spatial-transfer proxy only; not private-set validation or a leaderboard score.",
        "promotion_gate": {
            "baseline_must_reproduce_prior_h42_each_fold_within_1e-5": reproduction_ok,
            "same_run_mean_delta_at_least_0_005": mean_c - mean_b >= 0.005,
            "h46a_wins_at_least_3_of_4_folds": sum(d > 0 for d in deltas) >= 3,
            "no_fold_more_than_0_010_worse": min(deltas) >= -0.010,
            "gate_passed": gate,
            "submission_slot_authorized": False,
            "reason": "Even a local gate pass does not validate against private labels; no slot is automatically authorized.",
        },
        "incumbent_prior_reference": {"mean_dti": PRIOR_H42_MEAN, "fold_dti": PRIOR_H42_FOLDS,
                                      "same_run_mean_dti": round(mean_b, 6),
                                      "same_run_fold_dti": b,
                                      "fold_errors_vs_prior": prior_fold_errors},
        "h46a": {"mean_dti": round(mean_c, 6), "fold_dti": c,
                 "mean_delta_vs_same_run_incumbent": round(mean_c - mean_b, 6),
                 "fold_deltas": deltas, "wins": int(sum(d > 0 for d in deltas))},
        "folds": folds,
    }


def _write_submission(selected: np.ndarray, footprint: np.ndarray, profile: dict,
                      output_path: Path) -> dict:
    if selected.shape != footprint.shape or np.any(selected & ~footprint):
        raise ValueError("Selected cells must lie inside the output footprint")
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
        dst.set_band_description(1, "H46-A NGB pathfinder enrichment x TMI horizontal gradient; 40k packed pixels")
        dst.update_tags(
            submission_name="GEMSDOE43-H46A-NGB-TMI-40K-20261006",
            method="H46-A; pre-registered USGS NGB geochemical pathfinder enrichment x TMI horizontal gradient",
            validation="Public-catalogue blocked proxy only; not private-set validation or a leaderboard score",
            predictions="Binary 0/1 on the finite competition footprint; NaN nodata outside",
        )
    with rasterio.open(output_path) as out:
        values = out.read(1)
        finite = np.isfinite(values)
        checks = {
            "shape_matches_footprint": out.shape == footprint.shape,
            "single_band": out.count == 1,
            "dtype_float32": out.dtypes[0] == "float32",
            "crs_epsg_32611": out.crs is not None and out.crs.to_epsg() == 32611,
            "inside_cells_finite": bool(np.all(finite[footprint])),
            "outside_cells_nodata_nan": bool(np.isnan(values[~footprint]).all()),
            "inside_values_in_0_1": bool(np.all((values[footprint] >= 0) & (values[footprint] <= 1))),
            "grid_transform_preserved": tuple(out.transform) == tuple(profile["transform"]),
            "exactly_40000_predictions": int(np.count_nonzero(values[footprint] > 0)) == 40_000,
        }
        if not all(checks.values()):
            raise RuntimeError(f"Submission format validation failed: {checks}")
        record = {
            "path": str(output_path), "sha256": sha256(output_path),
            "bytes": output_path.stat().st_size, "prediction_pixels": int(np.count_nonzero(values[footprint] > 0)),
            "footprint_cells": int(footprint.sum()), "checks": checks,
            "grid": {"height": out.height, "width": out.width, "crs": out.crs.to_string(),
                     "transform": [float(x) for x in tuple(out.transform)[:6]],
                     "nodata": "NaN"},
        }
    return record


def run_experiment(*, features_path: Path, labels_path: Path, template_path: Path,
                   lidar_path: Path, csv_path: Path, submission_path: Path,
                   evidence_dir: Path) -> dict:
    """Disabled legacy H46-A entry point: its frozen source-count gates failed."""
    raise RuntimeError(
        "H46-A is stopped before holdout because its official NGB footprint sample-count gates failed; "
        "no labels are read here. Use the source-gated H46-B entry point in experiment_sgmc.py."
    )
    paths = {"features": features_path, "labels": labels_path,
             "template": template_path, "lidar": lidar_path}
    for name, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Missing {name} input: {path}")
    grids = _assert_aligned(paths)
    footprint, template_info = _read_footprint(template_path)
    labels = _load_labels(labels_path)
    if labels.shape != footprint.shape:
        raise ValueError("Label/footprint shape mismatch")
    baseline, baseline_report = _baseline_surface(features_path, lidar_path, footprint)
    candidate, candidate_report = _candidate_surface(features_path, csv_path, template_path, footprint)
    holdout = _score_folds(baseline, candidate, labels, footprint)

    # The submitted detector is label-free: one global pack from H46-A alone. Labels and the
    # incumbent are not blended into the emitted raster.
    final_selected = greedy_pack(candidate, footprint, min_sep=4.0, budget=40_000,
                                 candidate_cap=2_000_000)
    if int(final_selected.sum()) != 40_000:
        raise RuntimeError(f"Global H46-A pack emitted {int(final_selected.sum())}, expected 40,000")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    tif_receipt = _write_submission(final_selected, footprint, template_info["profile"], submission_path)

    dataset_receipt = {
        "competition_features": {"path": str(features_path), "bytes": features_path.stat().st_size,
                                 "sha256": sha256(features_path)},
        "labels": {"path": str(labels_path), "bytes": labels_path.stat().st_size,
                   "sha256": sha256(labels_path)},
        "sample_template": {"path": str(template_path), "bytes": template_path.stat().st_size,
                             "sha256": sha256(template_path), "use": "finite footprint/grid only; pixel values not used"},
        "lidar": {"path": str(lidar_path), "bytes": lidar_path.stat().st_size,
                  "sha256": sha256(lidar_path), "provenance": "USGS 3DEP-derived 12-band LiDAR scarp product; pinned sibling mirror"},
        "usgs_ngb_csv": {"path": str(csv_path), "bytes": csv_path.stat().st_size,
                         "sha256": sha256(csv_path), "official_url": "https://pubs.usgs.gov/of/2002/0227/ngb.csv"},
        "grid_metadata": grids,
        "template_footprint": {k: v for k, v in template_info.items() if k != "profile"},
    }
    source_report = {"candidate_source": candidate_report,
                     "usgs_source_sha256": dataset_receipt["usgs_ngb_csv"]["sha256"],
                     "official_url": dataset_receipt["usgs_ngb_csv"]["official_url"]}
    experiment_report = {
        "schema_version": 1,
        "experiment_id": "GEMSDOE43-H46A-NGB-TMI-40K-20261006",
        "run_timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python_version": sys.version,
        "platform": platform.platform(),
        "sources": dataset_receipt,
        "baseline_surface": baseline_report,
        "source_quality": source_report,
        "holdout": holdout,
        "submission": tif_receipt,
        "status": "local proxy run complete; score is not the DrivenData leaderboard score",
    }
    (evidence_dir / "data_manifest.json").write_text(json.dumps(dataset_receipt, indent=2, sort_keys=True) + "\n")
    (evidence_dir / "holdout.json").write_text(json.dumps(holdout, indent=2, sort_keys=True) + "\n")
    (evidence_dir / "submission_receipt.json").write_text(json.dumps(tif_receipt, indent=2, sort_keys=True) + "\n")
    (evidence_dir / "experiment.json").write_text(json.dumps(experiment_report, indent=2, sort_keys=True) + "\n")
    return experiment_report
