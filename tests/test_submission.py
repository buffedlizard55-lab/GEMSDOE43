import numpy as np
import rasterio
from rasterio.transform import from_origin

from gemsdoe43.experiment import _write_submission


def test_submission_writer_preserves_grid_and_marks_outside_as_nan(tmp_path):
    path = tmp_path / "candidate.tif"
    h, w = 250, 200
    foot = np.ones((h, w), dtype=bool)
    foot[:10, :20] = False
    selected = np.zeros_like(foot)
    selected.flat[:40_000] = True
    selected &= foot
    # Restore exactly 40k selected cells on the finite footprint.
    missing = 40_000 - int(selected.sum())
    if missing:
        candidates = np.flatnonzero(foot & ~selected)
        selected.ravel()[candidates[:missing]] = True
    profile = {
        "driver": "GTiff", "height": h, "width": w, "count": 1,
        "dtype": "float32", "crs": "EPSG:32611",
        "transform": from_origin(243350, 4508550, 100, 100), "nodata": np.nan,
    }
    receipt = _write_submission(selected, foot, profile, path)
    assert all(receipt["checks"].values())
    with rasterio.open(path) as ds:
        a = ds.read(1)
        assert ds.dtypes == ("float32",)
        assert ds.crs.to_epsg() == 32611
        assert np.isnan(a[~foot]).all()
        assert np.all((a[foot] >= 0) & (a[foot] <= 1))
        assert int((a[foot] > 0).sum()) == 40_000
