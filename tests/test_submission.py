"""Tests for the fail-closed GeoTIFF writer.

The contract under test is the organizer's submission format, verbatim from
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/>: one band, float32,
EPSG:32611, 100 m, the training bounds, values in [0, 1], and null/NaN outside the bounds.
Both outside-encodings are produced, and each is verified by re-reading the written bytes.
"""

from __future__ import annotations

import numpy as np
import pytest

from gems43 import submission
from gems43.grid import BOUNDS, EPSG, HEIGHT, SHAPE, TRANSFORM, WIDTH

# The writer is deliberately hard-wired to the competition grid -- that is one of the properties
# under test -- so these tests run on the real 3730 x 3292 shape with a sparse prediction.
H, W = SHAPE


N_DOTS = 300


def _world():
    rng = np.random.default_rng(0)
    foot = np.zeros((H, W), bool)
    foot[100:400, 200:600] = True                       # 90,000-cell stand-in footprint
    cat = np.zeros((H, W), bool)
    cat[250, 200:600] = True                            # a known fault crossing the footprint
    pred = np.zeros((H, W), dtype=np.float32)
    rows = rng.integers(100, 400, N_DOTS)
    cols = rng.integers(200, 600, N_DOTS)
    pred[rows, cols] = 1.0
    pred[250, :] = 0.0                                  # keep the known fault clear of stray dots
    n = min(N_DOTS, int((pred > 0).sum()))
    return foot, cat, pred, n


def test_writer_emits_both_encodings_and_both_pass(tmp_path):
    foot, cat, pred, n = _world()
    res = submission.write_submission(pred, foot, cat, "unit-test", outdir=tmp_path,
                                      make_zip=True)
    assert set(res["files"]) == {"zeros", "nan", "zip"}
    for mode in ("zeros", "nan"):
        a = res["files"][mode]
        assert a["all_checks_passed"] is True, a["checks"]
        assert a["emitted_positive_pixels"] == n
        assert a["checks"]["in_footprint_range_0_1"] is True
        assert a["checks"]["outside_footprint_compliant"] is True
    # only the zeros encoding can survive a whole-raster [0,1] predicate -- reported, not required
    assert res["files"]["zeros"]["informational"]["whole_raster_range_0_1"] is True
    assert res["files"]["nan"]["informational"]["whole_raster_range_0_1"] is False


def test_grid_identity_of_the_written_file(tmp_path):
    import rasterio

    foot, cat, pred, n = _world()
    res = submission.write_submission(pred, foot, cat, "t2", outdir=tmp_path, make_zip=False)
    with rasterio.open(tmp_path / "t2-zeros.tif") as src:
        assert src.count == 1
        assert src.dtypes[0] == "float32"
        assert (src.height, src.width) == (HEIGHT, WIDTH)
        assert src.crs.to_epsg() == EPSG
        # TRANSFORM is in Affine order, so compare the affine members and the bounds -- not
        # to_gdal(), which is the inverse permutation and would hide a transposed transform.
        assert tuple(np.round(tuple(src.transform)[:6], 6)) == tuple(np.round(TRANSFORM, 6))


def test_transform_matches_the_template(tmp_path):
    """Regression: ``TRANSFORM`` is in Affine (a,b,c,d,e,f) order.

    Passing it to ``Affine.from_gdal`` permutes it into a geotransform that is silently valid but
    puts the raster's top-left at (100, 0) with bounds reaching 1.7e10 -- and ``to_gdal()``
    round-trips the permutation, so a check written against ``to_gdal()`` passes anyway. This
    asserts the numeric bounds so the error cannot hide again, and cross-checks the template
    itself when the mirrored ``sample_submission.tif`` is present.
    """
    import rasterio

    from gems43 import bands

    foot, cat, pred, n = _world()
    submission.write_submission(pred, foot, cat, "t10", outdir=tmp_path, make_zip=False)
    with rasterio.open(tmp_path / "t10-zeros.tif") as src:
        assert tuple(np.round(tuple(src.transform)[:6], 6)) == tuple(np.round(TRANSFORM, 6))
        assert tuple(np.round(src.bounds, 6)) == tuple(np.round(BOUNDS, 6))

    try:                                  # the authoritative grid, from the hash-pinned mirror
        tpl = bands.raw_path("sample_submission.tif")
    except FileNotFoundError:
        pytest.skip("competition data mirror not restored; bounds asserted from the constant")
    if tpl.exists():
        with rasterio.open(tpl) as s:
            assert tuple(np.round(tuple(s.transform)[:6], 6)) == tuple(np.round(TRANSFORM, 6))
            assert tuple(np.round(s.bounds, 6)) == tuple(np.round(BOUNDS, 6))


def test_outside_footprint_encodings(tmp_path):
    import rasterio

    foot, cat, pred, n = _world()
    pred[0, 0] = 0.5                # garbage outside the footprint must be overwritten
    res = submission.write_submission(pred, foot, cat, "t3", outdir=tmp_path, make_zip=False)
    with rasterio.open(tmp_path / "t3-zeros.tif") as src:
        v = src.read(1)
    assert (v[~foot] == 0.0).all()
    with rasterio.open(tmp_path / "t3-nan.tif") as src:
        v = src.read(1)
    assert np.isnan(v[~foot]).all()


def test_in_footprint_values_are_bit_identical_across_encodings(tmp_path):
    import rasterio

    foot, cat, pred, n = _world()
    submission.write_submission(pred, foot, cat, "t4", outdir=tmp_path, make_zip=False)
    with rasterio.open(tmp_path / "t4-zeros.tif") as s:
        a = s.read(1)
    with rasterio.open(tmp_path / "t4-nan.tif") as s:
        b = s.read(1)
    assert np.array_equal(a[foot], b[foot])


def test_writer_clips_any_out_of_range_value_before_writing(tmp_path):
    import rasterio

    foot, cat, pred, n = _world()
    pred[150, 250] = 1.4
    pred[151, 251] = -0.3
    res = submission.write_submission(pred, foot, cat, "t5", outdir=tmp_path, make_zip=False)
    assert res["files"]["zeros"]["all_checks_passed"] is True
    with rasterio.open(tmp_path / "t5-zeros.tif") as s:
        v = s.read(1)
    assert v[150, 250] == 1.0 and v[151, 251] == 0.0


def test_writer_rejects_a_footprint_that_is_not_the_competition_grid(tmp_path):
    """Fail-closed on a programming error: the mask must be the full 3730 x 3292 grid."""
    foot, cat, pred, n = _world()
    with pytest.raises((ValueError, IndexError)):
        submission.write_submission(pred[:10, :10], foot[:10, :10], cat[:10, :10], "t9",
                                    outdir=tmp_path, make_zip=False)


def test_writer_clips_before_writing_so_a_valid_input_is_repaired(tmp_path):
    """The writer clips to [0,1] first, so a float round-off of 1+1e-7 does not abort the build."""
    foot, cat, pred, n = _world()
    pred[150, 250] = 1.0 + 1e-7
    res = submission.write_submission(pred, foot, cat, "t6", outdir=tmp_path, make_zip=False)
    assert res["files"]["zeros"]["all_checks_passed"] is True


def test_sentinel_and_nan_inside_the_footprint_are_repaired(tmp_path):
    foot, cat, pred, n = _world()
    pred[151, 251] = -3.4028234663852886e38   # the float32 sentinel the organizer uses for nodata
    pred[152, 252] = np.nan
    res = submission.write_submission(pred, foot, cat, "t7", outdir=tmp_path, make_zip=False)
    assert res["files"]["zeros"]["all_checks_passed"] is True


def test_catalogue_leakage_is_measured(tmp_path):
    foot, cat, pred, n = _world()
    pred[250, 300] = 1.0                       # one dot deliberately on a known fault
    res = submission.write_submission(pred, foot, cat, "t8", outdir=tmp_path, make_zip=False)
    assert res["files"]["zeros"]["on_catalogue_positive_pixels"] == 1
