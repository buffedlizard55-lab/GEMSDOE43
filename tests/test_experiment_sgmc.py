import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

import gemsdoe43.experiment as legacy_experiment
import gemsdoe43.experiment_sgmc as experiment_sgmc
from gemsdoe43.geology import GeologyRaster
from gemsdoe43.surface import empirical_percentile_surface, geometric_mean, smooth


def test_h46b_surface_is_fixed_h42_auxiliary_blend_and_respects_mask(monkeypatch, tmp_path):
    shape = (20, 20)
    footprint = np.ones(shape, dtype=bool)
    footprint[:2, :3] = False
    baseline = np.linspace(0.0, 1.0, num=shape[0] * shape[1], dtype=np.float32).reshape(shape)
    baseline[~footprint] = 0.0
    raw_tmi = np.arange(shape[0] * shape[1], dtype=np.float32).reshape(shape)
    contrast = np.zeros(shape, dtype=np.float32)
    contrast[:, 9:11] = 1.0
    contrast[~footprint] = 0.0
    report = {"unit_coverage_fraction": 1.0}
    gates = {"coverage": True}

    monkeypatch.setattr(experiment_sgmc, "contact_contrast", lambda *_: (contrast, report))
    monkeypatch.setattr(experiment_sgmc, "source_viability_gates", lambda _: gates)
    monkeypatch.setattr(experiment_sgmc, "read_band", lambda *_: raw_tmi.copy())

    candidate, candidate_report = experiment_sgmc._h46b_surface(
        features_path=tmp_path / "unused.tif",
        baseline_surface=baseline,
        unit_raster=GeologyRaster(np.ones(shape, dtype=np.uint32), [None, ("granite",)],
                                  [None, ("paleozoic", "paleozoic")], {}),
        footprint=footprint,
    )

    tmi_rank = empirical_percentile_surface(smooth(raw_tmi, 1.0), footprint)
    auxiliary = contrast * tmi_rank
    expected = geometric_mean(
        {"h42_incumbent": baseline, "sgmc_contact_tmi": auxiliary},
        {"h42_incumbent": 0.75, "sgmc_contact_tmi": 0.25},
    )
    expected[~footprint] = 0.0
    assert np.allclose(candidate, expected)
    assert np.all(candidate[~footprint] == 0.0)
    assert np.isfinite(candidate[footprint]).all()
    assert np.all((candidate[footprint] >= 0) & (candidate[footprint] <= 1))
    assert candidate_report["source_viability_gates"] == gates


def test_h46b_submission_writer_preserves_grid_and_tags_proxy_only(tmp_path):
    output_path = tmp_path / "unique-h46b.tif"
    height, width = 250, 200
    footprint = np.ones((height, width), dtype=bool)
    footprint[:10, :20] = False
    selected = np.zeros_like(footprint)
    selected.ravel()[:40_000] = True
    selected &= footprint
    missing = 40_000 - int(selected.sum())
    if missing:
        available = np.flatnonzero(footprint & ~selected)
        selected.ravel()[available[:missing]] = True
    profile = {
        "driver": "GTiff", "height": height, "width": width, "count": 1,
        "dtype": "float32", "crs": "EPSG:32611",
        "transform": from_origin(243350, 4508550, 100, 100), "nodata": np.nan,
    }

    receipt = experiment_sgmc._write_submission(selected, footprint, profile, output_path, False)

    assert all(receipt["checks"].values())
    assert receipt["private_set_validation"] is False
    assert receipt["leaderboard_score"] is None
    with rasterio.open(output_path) as dataset:
        values = dataset.read(1)
        assert dataset.dtypes == ("float32",)
        assert dataset.crs.to_epsg() == 32611
        assert np.isnan(values[~footprint]).all()
        assert np.all((values[footprint] >= 0) & (values[footprint] <= 1))
        assert int((values[footprint] > 0).sum()) == 40_000
        assert dataset.tags()["submission_name"] == experiment_sgmc.SUBMISSION_NAME
        assert dataset.tags()["validation"].startswith("Public-catalogue")


def test_stopped_h46a_entrypoint_fails_before_opening_any_inputs(tmp_path):
    with pytest.raises(RuntimeError, match="H46-A is stopped before holdout"):
        legacy_experiment.run_experiment(
            features_path=tmp_path / "missing-features.tif",
            labels_path=tmp_path / "missing-labels.tif",
            template_path=tmp_path / "missing-template.tif",
            lidar_path=tmp_path / "missing-lidar.tif",
            csv_path=tmp_path / "missing-ngb.csv",
            submission_path=tmp_path / "candidate.tif",
            evidence_dir=tmp_path / "evidence",
        )
