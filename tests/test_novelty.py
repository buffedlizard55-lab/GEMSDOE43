"""Tests for the near-duplicate screen.

The screen has to be *conservative*: it must fail (not pass) a layout that is a re-upload wearing
a different byte sequence. These tests pin down that direction for each metric, including the
stride-sampling shortcut used on very dense priors.
"""

from __future__ import annotations

import numpy as np
import pytest

from gems43 import novelty
from gems43.novelty import compare, coverage_iou_sparse, kernel_coverage, screen


def _dots(shape, idx):
    m = np.zeros(shape, bool)
    m.flat[idx] = True
    return m


SHAPE = (128, 128)          # >= 64 so the 64x64 block statistic is defined
NCELL = SHAPE[0] * SHAPE[1]


def test_kernel_coverage_matches_the_official_kernel():
    from gems43.grid import KERNEL_W, OFFSETS

    m = np.zeros(SHAPE, bool)
    m[30, 30] = True
    c = kernel_coverage(m)
    for (dr, dc), w in zip(OFFSETS, KERNEL_W):
        assert c[30 + dr, 30 + dc] == pytest.approx(w)
    assert c[0, 0] == 0.0


def test_identical_layouts_are_a_near_duplicate():
    idx = np.arange(0, NCELL, 31)          # enough dots for the 64x64 block statistic to exist
    a = _dots(SHAPE, idx)
    r = compare(a, a.copy(), "same")
    assert r.coverage_iou == pytest.approx(1.0)
    assert r.new_within_300m_of_prior == pytest.approx(1.0)
    assert r.verdict.startswith("NEAR-DUPLICATE")
    assert r.block_correlation == pytest.approx(1.0)


def test_a_one_pixel_translation_is_still_a_near_duplicate():
    """A byte-different file that is the same answer must not pass."""
    idx = np.arange(0, NCELL, 137)
    a = _dots(SHAPE, idx)
    b = _dots(SHAPE, (idx + 1) % NCELL)       # shift by one cell
    r = compare(a, b, "shifted")
    assert r.coverage_iou > 0.5, "a 1-px shift must be caught"
    assert r.verdict.startswith("NEAR-DUPLICATE")


def test_a_ten_percent_jitter_is_still_a_near_duplicate():
    rng = np.random.default_rng(0)
    idx = np.arange(0, 3600, 11)
    a = _dots(SHAPE, idx)
    j = idx.copy()
    move = rng.choice(idx.size, idx.size // 10, replace=False)
    j[move] = (j[move] + rng.integers(-2, 3, move.size)) % NCELL
    b = _dots(SHAPE, j)
    r = compare(a, b, "jittered")
    assert r.coverage_iou > 0.5
    assert r.verdict.startswith("NEAR-DUPLICATE")


def test_disjoint_layouts_are_distinct():
    a = _dots(SHAPE, np.arange(0, 2000))
    b = _dots(SHAPE, np.arange(12000, 14000))
    r = compare(a, b, "far")
    assert r.coverage_iou == pytest.approx(0.0)
    assert r.new_within_300m_of_prior == pytest.approx(0.0)
    assert r.median_nn_distance_px > 5
    assert r.verdict == "distinct"


def test_sparse_iou_equals_the_dense_definition():
    rng = np.random.default_rng(1)
    idx_a = rng.choice(NCELL, 120, replace=False)
    idx_b = rng.choice(NCELL, 90, replace=False)
    a, b = _dots(SHAPE, idx_a), _dots(SHAPE, idx_b)
    ca, cb = kernel_coverage(a), kernel_coverage(b)
    dense = float(np.minimum(ca, cb).sum() / np.maximum(ca, cb).sum())
    assert coverage_iou_sparse(a, b) == pytest.approx(dense, abs=1e-5)


def test_empty_sets_do_not_crash():
    a = _dots(SHAPE, np.array([1, 2, 3, 4, 5]))
    e = np.zeros(SHAPE, bool)
    assert coverage_iou_sparse(a, e) == 0.0
    assert coverage_iou_sparse(e, a) == 0.0
    r = compare(a, e, "empty")
    assert r.coverage_iou == 0.0


def test_screen_reports_the_worst_offender(tmp_path):
    """Two priors on disk: one an exact copy, one unrelated. The copy must drive the verdict."""
    import rasterio
    from gems43.grid import EPSG, TRANSFORM

    prof = dict(driver="GTiff", height=SHAPE[0], width=SHAPE[1], count=1, dtype="float32",
                crs=f"EPSG:{EPSG}", transform=rasterio.transform.Affine(*TRANSFORM))
    idx = np.arange(0, NCELL, 31)
    new = _dots(SHAPE, idx)
    with rasterio.open(tmp_path / "prior_copy.tif", "w", **prof) as d:
        d.write(new.astype("float32"), 1)
    other = _dots(SHAPE, np.arange(3, NCELL, 31))
    with rasterio.open(tmp_path / "prior_other.tif", "w", **prof) as d:
        d.write(other.astype("float32"), 1)
    foot = np.ones(SHAPE, bool)
    res = screen(new, tmp_path, foot)
    assert res["n_compared"] == 2
    assert res["worst_artifact"] == f"{tmp_path.name}:prior_copy.tif"
    assert res["worst_iou"] == pytest.approx(1.0)
    assert res["passed"] is False
    assert any("copy" in d for d in res["dupes"])


def test_stride_sampling_is_conservative_for_containment_but_not_for_iou():
    """Pins the documented asymmetry of the MAX_PRIOR_DOTS shortcut.

    Thinning a prior can only *lower* the 300 m containment and the nearest-neighbour distance,
    so on those two the shortcut cannot hide a duplicate.  It is NOT monotone for the coverage
    IoU: thinning shrinks the union faster than the intersection, so a dense, unrelated prior can
    report a *higher* IoU once sampled.  That direction produces false near-duplicates, which is
    why ``screen`` lists every sampled artifact in ``sampled_artifacts`` instead of hiding it.
    """
    rng = np.random.default_rng(3)
    idx = rng.choice(NCELL, 400, replace=False)
    a = _dots(SHAPE, idx)
    dense = _dots(SHAPE, rng.choice(NCELL, 3000, replace=False))
    full = compare(a, dense, "full")
    thin = compare(a, _dots(SHAPE, np.flatnonzero(dense.ravel())[::4]), "thin")
    # conservative direction: containment and NN distance can only fall when the prior is thinned
    assert thin.new_within_300m_of_prior <= full.new_within_300m_of_prior + 1e-9
    assert thin.median_nn_distance_px >= full.median_nn_distance_px - 1e-9
    # NOT conservative, and not predictable: the IoU moves, and which way it moves depends on
    # how dense the prior is relative to the new layout (it falls here, it rose in the 60 x 60
    # version of this same comparison). So a sampled comparison cannot be trusted to err on the
    # safe side, and every artifact it touches must be re-checked at full density.
    assert not np.isclose(thin.coverage_iou, full.coverage_iou)


def test_chance_level_and_excess_containment():
    """Excess containment is the statistic that separates coincidence from duplication.

    Two unrelated random layouts sit at the chance level, so their excess is about 0; an exact
    copy has excess 1 by construction. This is why the raw 0.60 containment threshold was
    retired: at K = 176k in the real footprint the chance level alone is 0.63, so a raw threshold
    cannot tell an unrelated prior from a duplicate.
    """
    rng = np.random.default_rng(7)
    a = _dots(SHAPE, rng.choice(NCELL, 300, replace=False))
    b = _dots(SHAPE, rng.choice(NCELL, 700, replace=False))
    r = compare(a, b, "random", n_eligible=NCELL)
    assert 0.0 < r.chance_new_in_prior < 1.0
    assert r.containment_excess < novelty.CONTAIN_EXCESS_LIMIT
    assert r.verdict == "distinct"

    same = compare(a, a.copy(), "copy", n_eligible=NCELL)
    assert same.containment_excess == pytest.approx(1.0)
    assert same.verdict.startswith("NEAR-DUPLICATE")


def test_excess_not_ratio_is_the_portable_statistic():
    """A ratio over chance has a density-dependent ceiling (an exact copy reaches only 1/chance,
    ~2.4x at these densities), so no fixed ratio threshold works. The excess does not."""
    rng = np.random.default_rng(11)
    for n in (200, 2000):
        a = _dots(SHAPE, rng.choice(NCELL, n, replace=False))
        r = compare(a, a.copy(), "copy", n_eligible=NCELL)
        assert r.containment_excess == pytest.approx(1.0), f"failed at n={n}"


def test_classify_separates_submissions_from_inputs():
    assert novelty.classify("GEMSDOE32:docs/downloads/gems32-abc.tif") == "submission"
    assert novelty.classify("7GEMSDOE:downloads/submission.tif") == "submission"
    assert novelty.classify("GEMSDOE24:data/external/derived_sgmc_faults_100m_u8.tif") == "input"
    assert novelty.classify("GEMSDOE4:data/evidence/newfault/seed42/prob_raw.tif") == (
        "intermediate")


def test_screen_reports_per_kind(tmp_path):
    import rasterio
    from gems43.grid import EPSG, TRANSFORM

    prof = dict(driver="GTiff", height=SHAPE[0], width=SHAPE[1], count=1, dtype="float32",
                crs=f"EPSG:{EPSG}", transform=rasterio.transform.Affine(*TRANSFORM))
    new = _dots(SHAPE, np.arange(0, NCELL, 31))
    for name, arr in (("submission/one.tif", new),
                      ("external/two_u8.tif", new)):
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(tmp_path / name, "w", **prof) as d:
            d.write(arr.astype("float32"), 1)
    res = screen(new, tmp_path, np.ones(SHAPE, bool))
    assert res["by_kind"]["submission"]["n"] == 1
    assert res["by_kind"]["input"]["n"] == 1
    assert res["worst_iou_submission"] == pytest.approx(1.0)
    assert res["passed"] is False        # an exact copy of a submission must fail the screen
