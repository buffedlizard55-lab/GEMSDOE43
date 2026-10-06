import csv

import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform

from gemsdoe43.geochem import (
    ASSAYS,
    Sample,
    _rank_within_group,
    project_to_template,
    read_ngb_csv,
    rasterize_local_enrichment,
)


def _make_csv(path):
    fields = [
        "'ID", "SAMPID", "SAMPTYP", "STUDY", "QUAD", "LONGITUDE", "LATITUDE",
    ]
    for assay in ASSAYS.values():
        fields.extend([assay, ""])
    rows = [fields]

    def sample(sid, typ, vals, flags=None, study="Hum"):
        flags = flags or {}
        row = [sid, sid, str(typ), study, "WIN", "-117.0", "40.0"]
        for element in ASSAYS:
            value = vals.get(element, "")
            flag = flags.get(element, "")
            row.extend([str(value), flag])
        rows.append(row)

    sample("s1", 50, {"Ag": 1, "As": 2, "Au": 3, "Pb": 4, "Sb": 5, "Zn": 6})
    sample("s2", 61, {"Ag": 2, "As": 3, "Au": 4, "Pb": 5, "Sb": 6, "Zn": 7},
           flags={"Ag": "*"})
    sample("s3", 100, {"Ag": 3, "As": "<0.2", "Au": "ND", "Pb": 6, "Sb": "B", "Zn": 8})
    sample("s4", 102, {"Ag": 4, "As": 5})  # fewer than three clean analytes
    sample("soil", 59, {"Ag": 9, "As": 9, "Au": 9, "Pb": 9, "Sb": 9, "Zn": 9})
    with path.open("w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(rows)


def test_tie_aware_percentile_ranks():
    assert np.allclose(_rank_within_group([1.0, 1.0, 3.0]), [0.25, 0.25, 1.0])
    assert _rank_within_group([5.0]) == [0.5]
    assert _rank_within_group([]) == []


def test_parser_excludes_substituted_censored_and_nonstream_samples(tmp_path):
    csv_path = tmp_path / "ngb.csv"
    _make_csv(csv_path)
    result = read_ngb_csv(csv_path)
    assert len(result.samples) == 4
    assert result.report["source_rows_excluding_header"] == 5
    assert result.report["header_irregularities"] == [
        "First CSV header cell is apostrophe-prefixed ('ID); normalized to the documented ID field"
    ]
    assert result.report["eligible_stream_rows_with_coordinates"] == 4
    assert result.report["valid_assay_samples_ge_3_of_6"] == 3
    assert result.report["assay_quality_counts"]["Ag"]["substituted"] == 1
    assert result.report["assay_quality_counts"]["As"]["censored"] == 1
    assert result.report["assay_quality_counts"]["Au"]["nonnumeric"] == 1
    assert result.samples[-1].index is None
    assert all(0.0 <= s.index <= 1.0 for s in result.samples if s.index is not None)


def test_projected_nad27_sample_lands_on_expected_template_cell(tmp_path):
    template = tmp_path / "grid.tif"
    data = np.zeros((100, 100), dtype=np.float32)
    data[:2] = np.nan
    with rasterio.open(
        template, "w", driver="GTiff", height=100, width=100, count=1,
        dtype="float32", crs="EPSG:32611", transform=from_origin(395000, 4405000, 100, 100),
        nodata=np.nan,
    ) as dst:
        dst.write(data, 1)
    lon, lat = transform("EPSG:32611", "EPSG:4267", [400000.0], [4400000.0])
    sample = Sample("p1", "Hum", 50, lon[0], lat[0], {}, index=0.9, usable_elements=6)
    mapped, report = project_to_template([sample], template, np.isfinite(data))
    assert len(mapped) == 1
    assert abs(mapped[0][1] - 50) <= 1
    assert abs(mapped[0][2] - 50) <= 1
    assert report["source_crs_assumption"] == "EPSG:4267"
    assert report["target_crs"] == "EPSG:32611"


def test_local_enrichment_respects_footprint_and_is_bounded():
    foot = np.ones((60, 80), dtype=bool)
    foot[:5] = False
    points = [
        (Sample("a", "Hum", 50, -117, 40, {}, index=0.95, usable_elements=6), 25, 30),
        (Sample("b", "Hum", 50, -117, 40, {}, index=0.90, usable_elements=5), 27, 31),
        (Sample("c", "WS", 50, -117, 40, {}, index=0.10, usable_elements=6), 45, 60),
    ]
    field, support, report = rasterize_local_enrichment(points, foot.shape, foot, sigma_px=3)
    assert field.dtype == np.float32
    assert np.isfinite(field).all()
    assert np.all((field >= 0) & (field <= 1))
    assert np.all(field[~foot] == 0)
    assert support.any()
    assert report["point_count_rasterized"] == 3
