"""Parse and rasterize the preregistered USGS NGB stream-sediment signal.

The CSV has blank-name qualifier columns: a substituted value is marked with `*` in
 the column immediately after its assay. We intentionally parse rows positionally rather
 than with DictReader so those qualifiers cannot disappear into a duplicate/None key.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

# A fixed trace-element suite and fixed assay preference, frozen in
# research/PREREGISTRATION-2026-10-06.md. Partial ICP has lower detection limits for
# trace elements; Au uses the dataset's graphite-furnace AA assay.
ASSAYS: dict[str, str] = {
    "Ag": "Ag(part)_ppm",
    "As": "As(part)_ppm",
    "Au": "Au_AA",
    "Pb": "Pb(part)_ppm",
    "Sb": "Sb(part)_ppm",
    "Zn": "Zn(part)_ppm",
}
STREAM_TYPES = frozenset({50, 61, 100, 102})
SOURCE_CRS = "EPSG:4267"  # USGS metadata: longitude/latitude are assumed NAD27.


@dataclass(frozen=True)
class Sample:
    sample_id: str
    study: str
    sample_type: int
    longitude: float
    latitude: float
    values: dict[str, float]
    index: float | None = None
    usable_elements: int = 0


@dataclass
class SampleSet:
    samples: list[Sample]
    report: dict


def _numeric(value: str, qualifier: str) -> tuple[float | None, str]:
    """Return a clean numeric assay, excluding official substitutions/censoring."""
    raw = value.strip()
    flag = qualifier.strip()
    if "*" in flag or "*" in raw:
        return None, "substituted"
    if not raw:
        return None, "blank"
    # Values such as ND, B, <x and >x are not continuous measurements. Do not replace
    # them with a detection-limit constant or an inferred half-limit.
    if any(ch in raw for ch in "<>~"):
        return None, "censored"
    try:
        result = float(raw.replace(",", ""))
    except ValueError:
        return None, "nonnumeric"
    if not math.isfinite(result) or result < 0:
        return None, "invalid"
    return result, "numeric"


def _as_int(value: str) -> int | None:
    try:
        f = float(value.strip())
    except (ValueError, AttributeError):
        return None
    if not math.isfinite(f) or not f.is_integer():
        return None
    return int(f)


def _rank_within_group(values: list[float]) -> list[float]:
    """Tie-aware empirical percentile ranks on [0,1]; a singleton receives 0.5."""
    x = np.asarray(values, dtype=np.float64)
    if x.size == 0:
        return []
    if x.size == 1:
        return [0.5]
    ordered = np.sort(x, kind="mergesort")
    left = np.searchsorted(ordered, x, side="left")
    right = np.searchsorted(ordered, x, side="right")
    ranks = (left + right - 1.0) / (2.0 * (x.size - 1.0))
    return ranks.tolist()


def read_ngb_csv(path: str | Path) -> SampleSet:
    """Read eligible stream-sediment rows and compute the locked six-assay index.

    Percentile ranks are calculated independently within each `STUDY` and for each
    assay, over all eligible stream-sediment records in the source CSV (not just the
    competition footprint). A sample index is the unweighted mean of its available
    assay ranks and requires at least three of six fields.
    """
    path = Path(path)
    status_counts: dict[str, dict[str, int]] = {
        element: {k: 0 for k in ("numeric", "substituted", "blank", "censored", "nonnumeric", "invalid")}
        for element in ASSAYS
    }
    rows_seen = 0
    type_counts: dict[str, int] = {}
    study_counts: dict[str, int] = {}
    parse_issues: dict[str, int] = {"short_row": 0, "bad_type": 0, "bad_location": 0,
                                    "duplicate_id": 0, "unknown_study": 0}

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            header = [s.strip() for s in next(reader)]
        except StopIteration as exc:
            raise ValueError("USGS NGB CSV is empty") from exc
        required = {"ID", "STUDY", "SAMPTYP", "LONGITUDE", "LATITUDE", *ASSAYS.values()}
        missing = sorted(required - set(header))
        if missing:
            raise ValueError(f"USGS NGB schema is missing required columns: {missing}")
        col = {name: header.index(name) for name in required}
        assay_col = {el: header.index(name) for el, name in ASSAYS.items()}
        # The report specifies that qualifier flags occupy the next column. The current
        # CSV represents these with an empty header cell; fail closed if this changes.
        for element, idx in assay_col.items():
            if idx + 1 >= len(header) or header[idx + 1] != "":
                raise ValueError(f"Expected an empty adjacent USGS qualifier column after {ASSAYS[element]!r}")

        eligible: list[Sample] = []
        seen_ids: set[str] = set()
        for row in reader:
            rows_seen += 1
            if len(row) < len(header):
                parse_issues["short_row"] += 1
                row = row + [""] * (len(header) - len(row))
            sid = row[col["ID"]].strip()
            typ = _as_int(row[col["SAMPTYP"]])
            if typ is None:
                parse_issues["bad_type"] += 1
                continue
            type_counts[str(typ)] = type_counts.get(str(typ), 0) + 1
            if typ not in STREAM_TYPES:
                continue
            study = row[col["STUDY"]].strip()
            if not study:
                parse_issues["unknown_study"] += 1
                continue
            try:
                lon = float(row[col["LONGITUDE"]].strip())
                lat = float(row[col["LATITUDE"]].strip())
            except (ValueError, AttributeError):
                parse_issues["bad_location"] += 1
                continue
            if not math.isfinite(lon) or not math.isfinite(lat) or not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
                parse_issues["bad_location"] += 1
                continue
            if not sid:
                parse_issues["duplicate_id"] += 1
                continue
            if sid in seen_ids:
                parse_issues["duplicate_id"] += 1
                raise ValueError(f"Duplicate USGS primary-key ID: {sid}")
            seen_ids.add(sid)
            study_counts[study] = study_counts.get(study, 0) + 1
            values: dict[str, float] = {}
            for element, idx in assay_col.items():
                value, state = _numeric(row[idx], row[idx + 1])
                status_counts[element][state] += 1
                if value is not None:
                    values[element] = value
            eligible.append(Sample(sid, study, typ, lon, lat, values))

    # Per-study/per-element rank scores use all eligible source samples, not spatial labels.
    ranks: dict[tuple[str, str, str], float] = {}
    for study in sorted({s.study for s in eligible}):
        group = [s for s in eligible if s.study == study]
        for element in ASSAYS:
            measured = [(s.sample_id, s.values[element]) for s in group if element in s.values]
            element_ranks = _rank_within_group([v for _, v in measured])
            ranks.update({(study, sid, element): rank for (sid, _), rank in zip(measured, element_ranks)})

    scored: list[Sample] = []
    for sample in eligible:
        available = [ranks[(sample.study, sample.sample_id, element)]
                     for element in ASSAYS if (sample.study, sample.sample_id, element) in ranks]
        n = len(available)
        composite = float(np.mean(available, dtype=np.float64)) if n >= 3 else None
        scored.append(Sample(sample.sample_id, sample.study, sample.sample_type,
                             sample.longitude, sample.latitude, sample.values, composite, n))

    report = {
        "source_file": path.name,
        "source_rows_excluding_header": rows_seen,
        "eligible_stream_rows_with_coordinates": len(eligible),
        "valid_assay_samples_ge_3_of_6": sum(s.index is not None for s in scored),
        "stream_type_counts_before_media_filter": dict(sorted(type_counts.items(), key=lambda kv: int(kv[0]))),
        "eligible_study_counts": dict(sorted(study_counts.items())),
        "assay_fields": dict(ASSAYS),
        "assay_quality_counts": status_counts,
        "parse_issues": parse_issues,
        "rank_method": "tie-aware empirical percentiles within STUDY per assay; equal mean; require >=3/6",
        "excluded_sample_types": sorted(set(type_counts) - {str(i) for i in STREAM_TYPES}),
    }
    return SampleSet(scored, report)


def project_to_template(samples: Iterable[Sample], template_path: str | Path,
                        footprint: np.ndarray | None = None, *,
                        require_index: bool = True) -> tuple[list[tuple[Sample, int, int]], dict]:
    """Project NAD27 lon/lat to the template CRS and retain points inside its footprint.

    Set `require_index=False` only for a coverage audit that counts otherwise eligible
    stream-sediment sample locations even when fewer than three assays are usable.
    """
    import rasterio
    from rasterio.transform import rowcol
    from rasterio.warp import transform

    items = [s for s in samples if not require_index or s.index is not None]
    with rasterio.open(template_path) as ds:
        shape = ds.height, ds.width
        if footprint is None:
            template = ds.read(1)
            footprint = np.isfinite(template)
        else:
            footprint = np.asarray(footprint, dtype=bool)
        if footprint.shape != shape:
            raise ValueError(f"Footprint shape {footprint.shape} does not match template {shape}")
        if ds.crs is None:
            raise ValueError("Template has no CRS")
        xs, ys = transform(SOURCE_CRS, ds.crs, [s.longitude for s in items],
                           [s.latitude for s in items])
        rows, cols = rowcol(ds.transform, xs, ys)
        mapped: list[tuple[Sample, int, int]] = []
        outside_bounds = 0
        inside_bounds_outside_footprint = 0
        for sample, r0, c0 in zip(items, rows, cols):
            r, c = int(r0), int(c0)
            if r < 0 or r >= shape[0] or c < 0 or c >= shape[1]:
                outside_bounds += 1
            elif not footprint[r, c]:
                inside_bounds_outside_footprint += 1
            else:
                mapped.append((sample, r, c))
        report = {
            "source_crs_assumption": SOURCE_CRS,
            "target_crs": ds.crs.to_string(),
            "template_shape": list(shape),
            "template_bounds": [float(ds.bounds.left), float(ds.bounds.bottom),
                                float(ds.bounds.right), float(ds.bounds.top)],
            "template_transform": [float(x) for x in tuple(ds.transform)[:6]],
            "template_footprint_cells": int(np.count_nonzero(footprint)),
            "sample_locations_projected": len(items),
            "require_geochem_index": bool(require_index),
            "samples_outside_template_bounds": outside_bounds,
            "samples_inside_bounds_outside_footprint": inside_bounds_outside_footprint,
            "samples_in_footprint": len(mapped),
            "mapped_study_counts": dict(sorted({study: sum(s.study == study for s, _, _ in mapped)
                                                for study in {s.study for s, _, _ in mapped}}.items())),
            "distinct_20km_blocks_with_samples": len({(r // 200, c // 200) for _, r, c in mapped}),
        }
    return mapped, report


def rasterize_local_enrichment(mapped: Iterable[tuple[Sample, int, int]],
                               shape: tuple[int, int], footprint: np.ndarray,
                               sigma_px: float = 20.0) -> tuple[np.ndarray, np.ndarray, dict]:
    """Build the locked 2 km local mean-percentile enrichment raster.

    Each point is assigned to its containing 100 m grid cell (the source reports roughly
    55 m possible horizontal location error). A fixed 20-pixel Gaussian estimates the
    local mean of sample indices; values below the neutral rank mean 0.5 contribute zero.
    """
    from scipy.ndimage import gaussian_filter

    foot = np.asarray(footprint, dtype=bool)
    if foot.shape != shape:
        raise ValueError("Footprint shape mismatch")
    weighted_sum = np.zeros(shape, dtype=np.float32)
    count = np.zeros(shape, dtype=np.float32)
    n = 0
    for sample, r, c in mapped:
        if sample.index is None:
            continue
        weighted_sum[r, c] += np.float32(sample.index)
        count[r, c] += np.float32(1.0)
        n += 1
    smoothed_sum = gaussian_filter(weighted_sum, sigma=sigma_px, mode="constant", truncate=4.0)
    smoothed_count = gaussian_filter(count, sigma=sigma_px, mode="constant", truncate=4.0)
    local_mean = np.divide(smoothed_sum, smoothed_count,
                           out=np.full(shape, 0.5, dtype=np.float32),
                           where=smoothed_count > np.float32(1e-12))
    support = foot & (smoothed_count > np.float32(1e-12))
    enrichment = np.maximum(local_mean - np.float32(0.5), np.float32(0.0))
    if np.any(support):
        scale = float(np.percentile(enrichment[support], 95.0))
    else:
        scale = 0.0
    if not math.isfinite(scale) or scale <= 0:
        field = np.zeros(shape, dtype=np.float32)
    else:
        field = np.clip(enrichment / np.float32(scale), 0.0, 1.0).astype(np.float32)
    field[~foot] = 0.0
    report = {
        "point_count_rasterized": n,
        "kernel_sigma_pixels": float(sigma_px),
        "kernel_sigma_m": float(sigma_px * 100.0),
        "gaussian_truncate_sigma": 4.0,
        "cells_with_geochemical_support": int(np.count_nonzero(support)),
        "support_fraction_of_footprint": float(np.count_nonzero(support) / max(1, np.count_nonzero(foot))),
        "positive_enrichment_cells": int(np.count_nonzero((field > 0) & foot)),
        "enrichment_p95_before_scaling": scale,
        "field_max": float(field.max(initial=0.0)),
        "outside_footprint_nonzero_cells": int(np.count_nonzero(field[~foot])),
    }
    return field, support, report
