"""Read official SGMC state polygons and derive label-free lithology/age contact evidence."""
from __future__ import annotations

import csv
import warnings
import zipfile
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

import numpy as np
import rasterio
import shapefile
from rasterio.crs import CRS
from rasterio.features import rasterize
from rasterio.warp import transform_bounds, transform_geom


UNKNOWN = frozenset({"", "null", "none", "na", "n/a", "unknown", "undetermined", "not determined"})
BATCH_SIZE = 512


@dataclass
class GeologyRaster:
    """Rasterized unit IDs plus source-standardized classes indexed by unit ID."""

    unit_id: np.ndarray
    lithology_signature: list[tuple[str, ...] | None]
    age_signature: list[tuple[str, str] | None]
    report: dict


def _norm(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.casefold() in UNKNOWN:
        return ""
    return text


def _norm_link(value: object) -> str:
    text = _norm(value)
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    return text.casefold()


def _fields(reader: shapefile.Reader) -> dict[str, str]:
    return {str(field[0]).strip().casefold(): str(field[0]) for field in reader.fields[1:]}


def _find_csv(root: Path, stem: str) -> Path:
    aliases = {"lith": {"lith", "lithology"}, "lithology": {"lith", "lithology"}}
    expected = aliases.get(stem.casefold(), {stem.casefold()})
    hits = sorted(
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.casefold() == ".csv"
        and any(p.stem.casefold() == value or p.stem.casefold().endswith("_" + value)
                for value in expected)
    )
    if not hits:
        raise ValueError(f"SGMC archive is missing {stem}.csv")
    if len(hits) > 1:
        # State archives may contain duplicated tables under alternate export folders;
        # accept them only if byte-identical, so the join choice remains deterministic.
        digests = {p.read_bytes() for p in hits}
        if len(digests) != 1:
            raise ValueError(f"SGMC archive has multiple non-identical {stem}.csv tables: {hits}")
    return hits[0]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"SGMC table has no header: {path}")
        output = []
        for row in reader:
            output.append({str(k).strip().casefold(): (v or "").strip() for k, v in row.items() if k is not None})
    return output


def _state_classes(root: Path, state: str) -> tuple[dict[tuple[str, str], tuple[str, ...]], dict[tuple[str, str], tuple[str, str]], dict]:
    age_path = _find_csv(root, "age")
    lith_path = _find_csv(root, "lith")
    age_rows = _read_csv(age_path)
    lith_rows = _read_csv(lith_path)
    for name, rows, required in (
        ("age", age_rows, {"state", "unit_link", "min_era", "max_era"}),
        ("lith", lith_rows, {"state", "unit_link", "lith_rank", "lith1"}),
    ):
        fields = set(rows[0]) if rows else set()
        missing = sorted(required - fields)
        if missing:
            raise ValueError(f"SGMC {state} {name}.csv is missing required fields {missing}; fields={sorted(fields)}")

    lith_parts: dict[tuple[str, str], set[str]] = {}
    for row in lith_rows:
        if row.get("lith_rank", "").strip().casefold() != "major":
            continue
        lith = _norm(row.get("lith1"))
        link = _norm_link(row.get("unit_link"))
        row_state = _norm(row.get("state")).upper() or state
        if lith and link:
            lith_parts.setdefault((row_state, link), set()).add(lith.casefold())
    lith_by_unit = {key: tuple(sorted(values)) for key, values in lith_parts.items()}

    age_by_unit: dict[tuple[str, str], tuple[str, str]] = {}
    for row in age_rows:
        link = _norm_link(row.get("unit_link"))
        row_state = _norm(row.get("state")).upper() or state
        low, high = _norm(row.get("min_era")), _norm(row.get("max_era"))
        if link and low and high:
            age_by_unit[(row_state, link)] = (low.casefold(), high.casefold())

    return lith_by_unit, age_by_unit, {
        "age_table": age_path.name,
        "lith_table": lith_path.name,
        "age_rows": len(age_rows),
        "lith_rows": len(lith_rows),
        "age_units_with_era_pair": len(age_by_unit),
        "units_with_major_lith1": len(lith_by_unit),
        "lith_rank_filter": "major only; exact case-insensitive match",
        "class_fields": {"lithology": "lith.lith1", "age": ["age.min_era", "age.max_era"]},
    }


def _find_polygon_shapefile(root: Path) -> Path:
    candidates = [
        p for p in root.rglob("*")
        if p.is_file() and p.suffix.casefold() == ".shp"
        and "geol_poly" in p.stem.casefold()
        and not any(token in p.stem.casefold() for token in ("complex", "tiled"))
    ]
    matches = sorted(candidates, key=lambda p: (p.stem.casefold() != "geol_poly", p.as_posix()))
    if not matches:
        candidates = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.shp"))
        raise ValueError(f"SGMC archive is missing geol_poly.shp; shapefile candidates={candidates[:80]}")
    if len(matches) > 1:
        raise ValueError(f"SGMC archive has multiple geol_poly.shp files: {matches}")
    return matches[0]


def _intersects(bounds_a: Iterable[float], bounds_b: Iterable[float]) -> bool:
    left_a, bottom_a, right_a, top_a = (float(x) for x in bounds_a)
    left_b, bottom_b, right_b, top_b = (float(x) for x in bounds_b)
    return left_a <= right_b and right_a >= left_b and bottom_a <= top_b and top_a >= bottom_b


def load_sgmc_unit_raster(
    archive_paths: dict[str, Path],
    *,
    tables_archive: Path,
    out_shape: tuple[int, int],
    transform: rasterio.Affine,
    target_crs: CRS | str,
    bounds: Iterable[float],
) -> GeologyRaster:
    """Join and rasterize CA/NV SGMC unit polygons onto the official competition grid.

    The caller supplies only the finite-grid geometry, not labels. Raster code 0 is
    reserved for unmapped pixels; positive codes are unique `(state, unit_link)` keys.
    """
    target_crs = CRS.from_user_input(target_crs)
    unit_id = np.zeros(out_shape, dtype=np.uint32)
    lithology_signature: list[tuple[str, ...] | None] = [None]
    age_signature: list[tuple[str, str] | None] = [None]
    unit_codes: dict[tuple[str, str], int] = {}
    state_reports: dict[str, dict] = {}
    total_features_seen = 0
    total_features_bbox = 0
    total_features_rasterized = 0
    total_transform_errors = 0
    total_missing_links = 0
    total_rasterize_warnings = 0

    tables_archive = Path(tables_archive)
    if not tables_archive.is_file():
        raise FileNotFoundError(f"Missing official SGMC attribute-table archive: {tables_archive}")
    with TemporaryDirectory(prefix="sgmc-") as temp_name:
        temp_root = Path(temp_name)
        tables_root = temp_root / "tables"
        tables_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tables_archive) as tables_zip:
            bad_member = tables_zip.testzip()
            if bad_member:
                raise ValueError(f"Corrupt SGMC tables ZIP member: {bad_member}")
            table_archive_members = tables_zip.namelist()
            tables_zip.extractall(tables_root)
        for state, archive in sorted(archive_paths.items()):
            state = state.upper()
            archive = Path(archive)
            if state not in {"CA", "NV"}:
                raise ValueError(f"Unexpected SGMC state key: {state}")
            extracted = temp_root / state
            extracted.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as zf:
                bad_member = zf.testzip()
                if bad_member:
                    raise ValueError(f"Corrupt ZIP member in {archive.name}: {bad_member}")
                zf.extractall(extracted)
                archive_members = zf.namelist()
            poly_path = _find_polygon_shapefile(extracted)
            prj_candidates = [p for p in poly_path.parent.iterdir()
                              if p.stem.casefold() == poly_path.stem.casefold()
                              and p.suffix.casefold() == ".prj"]
            if not prj_candidates:
                raise ValueError(f"SGMC {state} geol_poly shapefile has no .prj CRS file")
            prj_path = prj_candidates[0]
            source_crs = CRS.from_wkt(prj_path.read_text(encoding="utf-8", errors="replace"))
            source_bounds = transform_bounds(
                target_crs, source_crs, *tuple(float(v) for v in bounds), densify_pts=21
            )
            lith_by_unit, age_by_unit, table_report = _state_classes(tables_root, state)
            reader = shapefile.Reader(str(poly_path), encoding="latin1")
            field_map = _fields(reader)
            if "unit_link" not in field_map:
                raise ValueError(f"SGMC {state} geol_poly is missing unit_link; fields={sorted(field_map)}")
            if "state" not in field_map:
                raise ValueError(f"SGMC {state} geol_poly is missing state; fields={sorted(field_map)}")
            if reader.shapeType not in {shapefile.POLYGON, shapefile.POLYGONM, shapefile.POLYGONZ}:
                raise ValueError(f"SGMC {state} geol_poly is not a polygon layer (shapeType={reader.shapeType})")

            batch: list[tuple[dict, int]] = []
            state_features_seen = 0
            state_features_bbox = 0
            state_features_rasterized = 0
            state_transform_errors = 0
            state_missing_links = 0
            state_rasterize_warnings = 0
            for feature_index, shape_record in enumerate(reader.iterShapeRecords()):
                state_features_seen += 1
                shape = shape_record.shape
                if not shape.points or len(shape.bbox) != 4 or not _intersects(shape.bbox, source_bounds):
                    continue
                state_features_bbox += 1
                attrs = shape_record.record.as_dict()
                attrs = {str(k).strip().casefold(): v for k, v in attrs.items()}
                row_state = _norm(attrs.get("state")).upper() or state
                raw_link = _norm(attrs.get("unit_link"))
                if raw_link:
                    link = _norm_link(raw_link)
                    key = (row_state, link)
                else:
                    # Retain geometry coverage, but keep unjoinable polygons unclassified.
                    key = (row_state, f"__missing__{feature_index}")
                    state_missing_links += 1
                if key not in unit_codes:
                    code = len(lithology_signature)
                    if code >= np.iinfo(np.uint32).max:
                        raise OverflowError("Too many SGMC unit keys for uint32 rasterization")
                    unit_codes[key] = code
                    lithology_signature.append(lith_by_unit.get(key))
                    age_signature.append(age_by_unit.get(key))
                geom = shape.__geo_interface__
                try:
                    projected = transform_geom(source_crs, target_crs, geom)
                except Exception:
                    state_transform_errors += 1
                    continue
                batch.append((projected, unit_codes[key]))
                if len(batch) >= BATCH_SIZE:
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter("always")
                        rasterize(batch, out=unit_id, transform=transform, all_touched=False,
                                  dtype="uint32", skip_invalid=True)
                    state_rasterize_warnings += len(caught)
                    state_features_rasterized += len(batch)
                    batch.clear()
            if batch:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    rasterize(batch, out=unit_id, transform=transform, all_touched=False,
                              dtype="uint32", skip_invalid=True)
                state_rasterize_warnings += len(caught)
                state_features_rasterized += len(batch)
                batch.clear()
            reader.close()
            state_reports[state] = {
                **table_report,
                "archive": archive.name,
                "archive_member_count": len(archive_members),
                "polygon_shapefile": poly_path.relative_to(extracted).as_posix(),
                "source_crs": source_crs.to_string(),
                "polygon_fields": sorted(field_map),
                "polygon_shape_count": state_features_seen,
                "polygon_bboxes_intersecting_grid": state_features_bbox,
                "polygon_geometries_transformed": state_features_rasterized,
                "missing_unit_link_bboxes_intersecting_grid": state_missing_links,
                "geometry_transform_errors": state_transform_errors,
                "rasterization_warnings": state_rasterize_warnings,
            }
            total_features_seen += state_features_seen
            total_features_bbox += state_features_bbox
            total_features_rasterized += state_features_rasterized
            total_transform_errors += state_transform_errors
            total_missing_links += state_missing_links
            total_rasterize_warnings += state_rasterize_warnings

    if not unit_codes:
        raise ValueError("No SGMC unit polygons intersect the target grid bounds")
    return GeologyRaster(
        unit_id=unit_id,
        lithology_signature=lithology_signature,
        age_signature=age_signature,
        report={
            "states": state_reports,
            "attribute_table_archive": {
                "name": tables_archive.name,
                "member_count": len(table_archive_members),
                "members": table_archive_members,
            },
            "target_crs": target_crs.to_string(),
            "target_shape": list(out_shape),
            "target_transform": [float(v) for v in tuple(transform)[:6]],
            "unit_key_count_in_grid_bounds": len(unit_codes),
            "polygon_shape_count_total": total_features_seen,
            "polygon_bboxes_intersecting_grid": total_features_bbox,
            "polygon_geometries_transformed": total_features_rasterized,
            "polygon_geometry_transform_errors": total_transform_errors,
            "polygons_missing_unit_link_in_grid_bounds": total_missing_links,
            "rasterization_warnings": total_rasterize_warnings,
        },
    )


def contact_contrast(unit_id: np.ndarray, geology: GeologyRaster, footprint: np.ndarray) -> tuple[np.ndarray, dict]:
    """Compute four-neighbour unit-boundary contrast without using fault labels."""
    unit_id = np.asarray(unit_id)
    footprint = np.asarray(footprint, dtype=bool)
    if unit_id.ndim != 2 or unit_id.shape != footprint.shape or unit_id.shape != geology.unit_id.shape:
        raise ValueError("unit_id, geology raster, and footprint must be same-size 2-D arrays")
    n_codes = len(geology.lithology_signature)
    if n_codes != len(geology.age_signature) or int(unit_id.max(initial=0)) >= n_codes:
        raise ValueError("SGMC class lookup does not cover all rasterized unit codes")

    lith_code = np.zeros(n_codes, dtype=np.uint32)
    age_code = np.zeros(n_codes, dtype=np.uint32)
    lith_groups: dict[tuple[str, ...], int] = {}
    age_groups: dict[tuple[str, str], int] = {}
    lith_valid = np.zeros(n_codes, dtype=bool)
    age_valid = np.zeros(n_codes, dtype=bool)
    for code in range(1, n_codes):
        lith = geology.lithology_signature[code]
        age = geology.age_signature[code]
        if lith:
            lith_code[code] = lith_groups.setdefault(lith, len(lith_groups) + 1)
            lith_valid[code] = True
        if age:
            age_code[code] = age_groups.setdefault(age, len(age_groups) + 1)
            age_valid[code] = True

    strength = np.zeros(unit_id.shape, dtype=np.float32)
    boundary_pair_count = 0
    known_lith_components = 0
    known_age_components = 0

    def apply_pairs(a: np.ndarray, b: np.ndarray, left: tuple[slice, slice], right: tuple[slice, slice]) -> None:
        nonlocal boundary_pair_count, known_lith_components, known_age_components
        boundary = (a > 0) & (b > 0) & (a != b)
        if not boundary.any():
            return
        av, bv = a[boundary], b[boundary]
        lith_known = lith_valid[av] & lith_valid[bv]
        age_known = age_valid[av] & age_valid[bv]
        known = lith_known.astype(np.uint8) + age_known.astype(np.uint8)
        lith_diff = lith_known & (lith_code[av] != lith_code[bv])
        age_diff = age_known & (age_code[av] != age_code[bv])
        numerator = lith_diff.astype(np.float32) + age_diff.astype(np.float32)
        values = np.divide(numerator, known, out=np.zeros_like(numerator), where=known > 0)
        # Store positive contrast only; zero-contrast contacts cannot raise a detector score.
        hit = values > 0
        if not hit.any():
            boundary_pair_count += int(boundary.sum())
            known_lith_components += int(lith_known.sum())
            known_age_components += int(age_known.sum())
            return
        left_view = strength[left]
        right_view = strength[right]
        # Work by flattened pair indices; each view has the same shape as `a`/`b`.
        boundary_rows, boundary_cols = np.nonzero(boundary)
        hit_rows, hit_cols = boundary_rows[hit], boundary_cols[hit]
        left_view[hit_rows, hit_cols] = np.maximum(left_view[hit_rows, hit_cols], values[hit])
        right_view[hit_rows, hit_cols] = np.maximum(right_view[hit_rows, hit_cols], values[hit])
        boundary_pair_count += int(boundary.sum())
        known_lith_components += int(lith_known.sum())
        known_age_components += int(age_known.sum())

    apply_pairs(unit_id[:, :-1], unit_id[:, 1:], (slice(None), slice(None, -1)),
                (slice(None), slice(1, None)))
    apply_pairs(unit_id[:-1, :], unit_id[1:, :], (slice(None, -1), slice(None)),
                (slice(1, None), slice(None)))
    strength[~footprint] = 0.0

    footprint_count = int(footprint.sum())
    covered = footprint & (unit_id > 0)
    both = np.zeros(unit_id.shape, dtype=bool)
    mapped = unit_id > 0
    if mapped.any():
        both[mapped] = lith_valid[unit_id[mapped]] & age_valid[unit_id[mapped]]
    report = {
        "footprint_cells": footprint_count,
        "mapped_unit_cells": int(covered.sum()),
        "unit_coverage_fraction": float(covered.sum() / max(1, footprint_count)),
        "cells_with_major_lith1_and_era_pair": int((footprint & both).sum()),
        "both_class_coverage_fraction": float((footprint & both).sum() / max(1, footprint_count)),
        "distinct_rasterized_unit_ids": int(np.unique(unit_id[covered]).size),
        "unit_boundary_adjacency_pairs": boundary_pair_count,
        "known_lithology_comparisons": known_lith_components,
        "known_age_comparisons": known_age_components,
        "positive_contrast_cells": int(np.count_nonzero((strength > 0) & footprint)),
        "contrast_max": float(strength.max(initial=0.0)),
        "outside_footprint_nonzero_cells": int(np.count_nonzero(strength[~footprint])),
        "contrast_definition": "mean of available major-lith1 and min/max-era categorical differences across four-neighbour unit boundaries; max incident contrast per cell",
    }
    return strength, report


def source_viability_gates(contrast_report: dict) -> dict[str, bool]:
    """Apply the frozen H46-B geometry/attribute/support gates."""
    return {
        "at_least_90_percent_polygon_coverage": contrast_report["unit_coverage_fraction"] >= 0.90,
        "at_least_60_percent_cells_have_lith_and_age": contrast_report["both_class_coverage_fraction"] >= 0.60,
        "at_least_5000_positive_contrast_cells": contrast_report["positive_contrast_cells"] >= 5_000,
        "outside_footprint_contact_strength_zero": contrast_report["outside_footprint_nonzero_cells"] == 0,
    }
