"""Tests for the spatially blocked validation frames.

The property that matters is that the O(K) scorer is *exactly* equal to the dense reference
implementation of the official metric, and that the frames behave as documented (no leakage of the
truth into the masked set, whole components held out, and so on).
"""

from __future__ import annotations

import numpy as np
import pytest

from gems43 import holdout
from gems43.holdout import Frame, blocks, connected_components, make_frames, score_dots, score_frame
from gems43.metric import dti_components


H = 240
W = 200


def _world(seed=0, H=H, W=W):
    rng = np.random.default_rng(seed)
    foot = np.ones((H, W), bool)
    foot[:3] = False
    cat = np.zeros((H, W), bool)
    # three long fault traces plus a short one, so component splitting is meaningful
    cat[20:130, 20] = True
    cat[30:120, 55] = True
    cat[10:80, 80] = True
    cat[150:170, 40] = True
    pred = np.zeros((H, W))
    idx = rng.choice(H * W, 900, replace=False)
    pred.flat[idx] = 1.0
    return foot, cat, pred


def test_blocks_partition_the_grid():
    for n in (2, 3, 4):
        b = blocks((H, W), n)
        assert b.shape == (H, W)
        assert set(np.unique(b)) == set(range(n * n))
        sizes = [int((b == i).sum()) for i in range(n * n)]
        assert max(sizes) - min(sizes) <= H * W * 0.02   # near-equal area


def test_connected_components_finds_the_traces():
    _, cat, _ = _world()
    lab, n = connected_components(cat)
    assert n == 4, "four disjoint traces"
    assert set(np.unique(lab[cat])) == set(range(1, n + 1))


def test_frame_a_holds_out_whole_components_and_masks_the_rest():
    foot, cat, _ = _world()
    frames = [f for f in make_frames(foot, cat, sgmc=None, n_side=2) if f.name.startswith("A")]
    assert frames, "frame A was not built"
    for f in frames:
        # truth and masked sets are disjoint and together are exactly the catalogue
        assert not (f.truth & f.masked).any()
        assert np.array_equal(f.truth | f.masked, cat)
        # the truth is exactly the catalogue pixels inside this block, so it is disjoint from
        # the pixels an out-of-fold model would have been trained on (the catalogue outside it)
        b = int(f.name[-1])
        in_block = blocks(foot.shape, 2) == b
        assert np.array_equal(f.truth, cat & in_block)
        assert not (f.truth & (cat & ~in_block)).any()


def test_frame_b_truth_is_off_catalogue():
    foot, cat, _ = _world()
    rng = np.random.default_rng(1)
    sgmc = np.zeros(foot.shape, dtype=np.uint8)
    sgmc[cat] = 1
    extra = rng.random(foot.shape) < 0.06
    sgmc[extra] = 1                      # an independent compilation: superset of the catalogue
    frames = [f for f in make_frames(foot, cat, sgmc=sgmc, n_side=2) if f.name.startswith("B")]
    assert frames
    for f in frames:
        assert not (f.truth & cat).any(), "frame B truth must be off-catalogue"
        assert (f.masked == cat).all(), "the whole catalogue is masked in frame B"


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_fast_scorer_equals_dense_reference(seed):
    foot, cat, pred = _world(seed)
    f = Frame("t", cat & (blocks(foot.shape, 2) == 0), cat & (blocks(foot.shape, 2) != 0), "x")
    dots = holdout.dots_from_pred(pred, f)      # masked pixels deleted, as the frame requires
    slow = score_frame(pred, f)                 # dense path
    fast = score_dots(dots, f)                  # O(K) path
    for k in ("tp_w", "fp_w", "fn_w", "dti"):
        assert slow[k] == pytest.approx(fast[k], abs=1e-6), k


def test_fast_scorer_handles_empty_emission():
    foot, cat, _ = _world()
    f = Frame("t", cat, np.zeros_like(cat), "x")
    r = score_dots(np.array([], dtype=np.int64), f)
    assert r["dti"] == 0.0
    assert r["fp_w"] == 0.0
    assert r["fn_w"] == pytest.approx(float(cat.sum()))


def test_masked_pixels_are_deleted_before_scoring():
    """A dot on a masked pixel can earn no credit and incur no penalty."""
    H = W = 40
    truth = np.zeros((H, W), bool)
    truth[20, 20] = True
    masked = np.zeros((H, W), bool)
    masked[20, 20] = True                        # the truth pixel is masked (a known fault)
    f = Frame("t", truth, masked, "x")
    pred = np.zeros((H, W))
    pred[20, 20] = 1.0
    c = dti_components(pred, truth)
    s = score_frame(pred, f)
    assert c.tp == pytest.approx(1.0)            # dense scorer ignores the mask
    assert s["tp_w"] == 0.0                      # the frame scorer deletes the masked dot
    assert s["n_emitted"] == 0


def test_fold_summary_statistics():
    rows = [{"dti": 0.1, "weighted_recall": 0.2, "credit_per_dot": 1.0},
            {"dti": 0.3, "weighted_recall": 0.4, "credit_per_dot": 2.0}]
    s = holdout.fold_summary(rows)
    assert s["folds"] == 2
    assert s["mean_dti"] == pytest.approx(0.2)
    assert s["min_dti"] == pytest.approx(0.1)
    assert s["max_dti"] == pytest.approx(0.3)
    assert holdout.fold_summary([]) == {}


def test_frame_kernel_is_the_fp_kernel():
    from gems43.grid import KERNEL_W, OFFSETS
    H = W = 30
    truth = np.zeros((H, W), bool)
    truth[15, 15] = True
    f = Frame("t", truth, np.zeros((H, W), bool), "x")
    k = holdout.frame_kernel(f)
    for (dr, dc), w in zip(OFFSETS, KERNEL_W):
        assert k[15 + dr, 15 + dc] == pytest.approx(w)
    assert k[0, 0] == 0.0
