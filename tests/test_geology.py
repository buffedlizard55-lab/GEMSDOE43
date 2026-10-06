import csv
import zipfile

import numpy as np
import shapefile
from rasterio.crs import CRS
from rasterio.transform import from_origin

from gemsdoe43.geology import (
    GeologyRaster,
    contact_contrast,
    load_sgmc_unit_raster,
    source_viability_gates,
)


def test_contact_contrast_uses_only_known_lithology_and_age_differences():
    units = np.array(
        [
            [1, 1, 2, 2],
            [1, 1, 2, 2],
            [3, 3, 4, 4],
        ],
        dtype=np.uint32,
    )
    lith = [None, ("granite",), ("basalt",), ("granite",), None]
    age = [None, ("paleozoic", "paleozoic"), ("mesozoic", "mesozoic"),
           ("paleozoic", "paleozoic"), ("cenozoic", "cenozoic")]
    geology = GeologyRaster(unit_id=units, lithology_signature=lith, age_signature=age, report={})
    footprint = np.ones(units.shape, dtype=bool)

    strength, report = contact_contrast(units, geology, footprint)

    # 1/2 differs in both known components; 1/3 differs only by unit ID, not class.
    assert np.all(strength[:, 1] == 1.0)
    assert strength[2, 0] == 0.0
    # 3/4 has no known lithology on one side, so only the age comparison is used.
    assert np.all(strength[2, 2:] == 1.0)
    assert report["positive_contrast_cells"] == 8
    assert report["outside_footprint_nonzero_cells"] == 0


def test_contact_contrast_is_zero_outside_finite_template_footprint():
    units = np.array([[1, 1, 2], [1, 1, 2]], dtype=np.uint32)
    geology = GeologyRaster(
        unit_id=units,
        lithology_signature=[None, ("granite",), ("basalt",)],
        age_signature=[None, ("paleozoic", "paleozoic"), ("mesozoic", "mesozoic")],
        report={},
    )
    footprint = np.array([[True, True, False], [True, False, False]])

    strength, report = contact_contrast(units, geology, footprint)

    assert np.all(strength[~footprint] == 0.0)
    assert report["outside_footprint_nonzero_cells"] == 0


def test_sgmc_source_viability_gates_are_explicit():
    report = {
        "unit_coverage_fraction": 0.91,
        "both_class_coverage_fraction": 0.62,
        "positive_contrast_cells": 6000,
        "outside_footprint_nonzero_cells": 0,
    }
    assert all(source_viability_gates(report).values())
    report["unit_coverage_fraction"] = 0.89
    assert not source_viability_gates(report)["at_least_90_percent_polygon_coverage"]


def test_load_sgmc_state_archive_reprojects_and_joins_attributes(tmp_path):
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    base = state_dir / "geol_poly"
    writer = shapefile.Writer(str(base), shapeType=shapefile.POLYGON)
    writer.field("state", "C", size=2)
    writer.field("unit_link", "C", size=16)
    writer.poly([[(0, 0), (2, 0), (2, 2), (0, 2), (0, 0)]])
    writer.record("CA", "unit_a")
    writer.poly([[(2, 0), (4, 0), (4, 2), (2, 2), (2, 0)]])
    writer.record("CA", "unit_b")
    writer.close()
    (state_dir / "geol_poly.prj").write_text(CRS.from_epsg(32611).to_wkt(), encoding="utf-8")

    for name, fields, rows in (
        ("age.csv", ["state", "unit_link", "min_era", "max_era"],
         [["CA", "unit_a", "Paleozoic", "Paleozoic"], ["CA", "unit_b", "Mesozoic", "Mesozoic"]]),
        ("lith.csv", ["state", "unit_link", "lith_rank", "lith1"],
         [["CA", "unit_a", "major", "Granite"], ["CA", "unit_b", "major", "Basalt"]]),
    ):
        with (state_dir / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(fields)
            writer.writerows(rows)

    archive = tmp_path / "CA.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for path in state_dir.iterdir():
            zf.write(path, path.name)
    tables_archive = tmp_path / "USGS_SGMC_Tables_CSV.zip"
    with zipfile.ZipFile(tables_archive, "w") as zf:
        zf.write(state_dir / "age.csv", "SGMC_Age.csv")
        zf.write(state_dir / "lith.csv", "SGMC_Lithology.csv")

    geology = load_sgmc_unit_raster(
        {"CA": archive},
        tables_archive=tables_archive,
        out_shape=(2, 4),
        transform=from_origin(0, 2, 1, 1),
        target_crs="EPSG:32611",
        bounds=(0, 0, 4, 2),
    )
    assert np.all(geology.unit_id[:, :2] == geology.unit_id[0, 0])
    assert np.all(geology.unit_id[:, 2:] == geology.unit_id[0, 2])
    assert geology.unit_id[0, 0] != geology.unit_id[0, 2]
    assert geology.lithology_signature[geology.unit_id[0, 0]] == ("granite",)
    assert geology.age_signature[geology.unit_id[0, 2]] == ("mesozoic", "mesozoic")
    strength, report = contact_contrast(
        geology.unit_id, geology, np.ones(geology.unit_id.shape, dtype=bool)
    )
    assert np.all(strength[:, 1:3] == 1.0)
    assert report["positive_contrast_cells"] == 4
