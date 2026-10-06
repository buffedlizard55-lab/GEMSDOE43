"""Unit tests for the official distance-weighted Tversky index.

Every expectation here is either the organizer's own published worked example or an
independent brute-force re-derivation of the same quantity -- nothing is asserted from memory.
"""

from __future__ import annotations

import numpy as np
import pytest

from gems43.grid import EPSG, HEIGHT, KERNEL_W, OFFSETS, R_PIXELS, WIDTH, shift
from gems43.metric import (
    disjoint_credit_dti,
    exact_dti_from_dot_credits,
    dti,
    dti_components,
    dti_from_components,
    implied_truth_size,
    marginal_threshold,
    required_recall,
)


# --------------------------------------------------------------------------------------
# 1. The organizer's published worked example
#    https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
#    "TP_w = 3.00, FP_w = 1.89, FN_w = 2.00 -> TI_w(0.2, 0.8) = 3.00/(3.00+0.2*1.89+0.8*2.00) = 0.60"
# --------------------------------------------------------------------------------------
def test_published_worked_example_arithmetic():
    got = dti_from_components(3.00, 1.89, 2.00)
    assert got == pytest.approx(3.00 / (3.00 + 0.2 * 1.89 + 0.8 * 2.00), rel=1e-12)
    assert round(got, 2) == 0.60


# --------------------------------------------------------------------------------------
# 2. Kernel geometry: R = 300 m on a 100 m grid == 3 pixels; 29 offsets; weights 1 - d/3
# --------------------------------------------------------------------------------------
def test_kernel_geometry():
    assert R_PIXELS == pytest.approx(3.0)
    assert OFFSETS.shape[0] == 29                       # integer lattice inside a radius-3 disc
    d = np.hypot(OFFSETS[:, 0].astype(float), OFFSETS[:, 1].astype(float))
    assert np.allclose(KERNEL_W, np.maximum(0.0, 1.0 - d / 3.0))
    assert KERNEL_W.max() == pytest.approx(1.0)         # the centre pixel
    assert (KERNEL_W == 0.0).sum() == 4                 # the four pixels at exactly 300 m


# --------------------------------------------------------------------------------------
# 3. The vectorised metric must equal a brute-force O(N*M) re-derivation
# --------------------------------------------------------------------------------------
def _bruteforce(pred: np.ndarray, truth: np.ndarray):
    rr, cc = np.nonzero(truth)
    pr, pc = np.nonzero(pred > 0)
    R = 300.0
    tp = 0.0
    fn = 0.0
    for r, c in zip(rr, cc):
        best = 0.0
        for r2, c2 in zip(pr, pc):
            d = 100.0 * np.hypot(r - r2, c - c2)
            if d <= R:
                best = max(best, pred[r2, c2] * (1.0 - d / R))
        tp += best
        fn += 1.0 - best
    fp = 0.0
    for r2, c2 in zip(pr, pc):
        best = 0.0
        for r, c in zip(rr, cc):
            d = 100.0 * np.hypot(r - r2, c - c2)
            best = max(best, (1.0 - d / R) if d <= R else 0.0)
        fp += pred[r2, c2] * (1.0 - best)
    return tp, fp, fn


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_metric_matches_bruteforce(seed):
    rng = np.random.default_rng(seed)
    H = W = 26
    truth = rng.random((H, W)) < 0.06
    pred = np.zeros((H, W))
    idx = rng.choice(H * W, size=40, replace=False)
    pred.flat[idx] = rng.random(40)
    got = dti_components(pred, truth)
    tp, fp, fn = _bruteforce(pred, truth)
    assert got.tp == pytest.approx(tp, abs=1e-9)
    assert got.fp == pytest.approx(fp, abs=1e-9)
    assert got.fn == pytest.approx(fn, abs=1e-9)


# --------------------------------------------------------------------------------------
# 4. The three algebraic consequences this package relies on
# --------------------------------------------------------------------------------------
def test_fn_equals_g_minus_tp():
    rng = np.random.default_rng(7)
    H = W = 30
    truth = rng.random((H, W)) < 0.05
    pred = (rng.random((H, W)) < 0.05) * rng.random((H, W))
    c = dti_components(pred, truth)
    assert c.fn == pytest.approx(c.n_truth - c.tp, abs=1e-9)


def test_denominator_identity_and_marginal_cost():
    """Consequence (2).

    With ``D = 0.2*TP + 0.2*FP + 0.8*|G|``, a newly-called pixel of weight ``p`` whose best
    kernel credit is ``k`` raises ``TP`` by ``p*k`` and ``FP`` by ``p*(1-k)``, so ``dD = 0.2*p``
    *exactly*, independent of where the pixel lands.  Constructed on an isolated truth pixel so
    that the credit is provably new.
    """
    H = W = 60
    truth = np.zeros((H, W), bool)
    truth[30, 30] = True                      # a single isolated truth pixel
    base = np.zeros((H, W))
    b = dti_components(base, truth)
    for p in (1.0, 0.7, 0.4):
        for (r, c) in [(30, 30), (30, 31), (30, 32)]:   # k = 1, 2/3, 1/3
            alt = base.copy()
            alt[r, c] = p
            got = dti_components(alt, truth)
            assert got.denominator - b.denominator == pytest.approx(0.2 * p, abs=1e-9)
            k = 1.0 - np.hypot(r - 30, c - 30) / 3.0
            assert got.tp == pytest.approx(p * k, abs=1e-9)
            # and the move pays iff k > 0.2 * s
            assert (got.dti > b.dti) == (k > 0.2 * b.dti)


def test_marginal_rule_is_alpha_times_score():
    """A pixel of weight p and credit k pays iff k > 0.2*s, independent of p."""
    rng = np.random.default_rng(3)
    H = W = 40
    truth = np.zeros((H, W), bool)
    truth[:, 20] = True                       # a straight vertical fault
    base = np.zeros((H, W))
    base[10, 18] = 1.0                        # one dot, 200 m from the fault -> k = 1/3
    s0 = dti(base, truth)
    for p in (1.0, 0.5, 0.1):
        alt = base.copy()
        alt[30, 22] = p                       # also 200 m away, k = 1/3, new truth pixel
        assert (dti(alt, truth) > s0) == (1.0 / 3.0 > 0.2 * s0)
    assert marginal_threshold(s0) == pytest.approx(0.2 * s0)


def test_disjoint_credit_reduction_and_its_error_sign():
    """The reduction equals the true index iff sum_i k_i == T; the error sign is predictable.

    Regime 1 (fewer dots than truth pixels):  sum_i k_i < T  ->  reduction is OPTIMISTIC.
    Regime 2 (several dots per truth pixel):  sum_i k_i > T  ->  reduction is PESSIMISTIC.
    """
    rng = np.random.default_rng(5)
    H = W = 40
    # Regime 1: a handful of dots, a dense truth network
    truth = rng.random((H, W)) < 0.10
    pred = np.zeros((H, W))
    pred.flat[rng.choice(H * W, 12, replace=False)] = 1.0
    c = dti_components(pred, truth)
    red = disjoint_credit_dti(c.tp, c.n_emitted, c.n_truth)
    sum_k = c.n_emitted - c.fp                       # F = |S| - sum_i k_i
    assert sum_k < c.tp, "regime 1 precondition"
    assert c.dti < red + 1e-9
    assert exact_dti_from_dot_credits(c.tp, c.n_emitted, sum_k, c.n_truth) == pytest.approx(c.dti)

    # Regime 2: many dots stacked inside the kernel of few truth pixels
    truth2 = np.zeros((H, W), bool)
    truth2[20, 20] = True
    pred2 = np.zeros((H, W))
    pred2[19:22, 19:22] = 1.0                        # 9 dots, one of them exactly on the truth
    c2 = dti_components(pred2, truth2)
    sum_k2 = c2.n_emitted - c2.fp
    assert sum_k2 > c2.tp, "regime 2 precondition"
    red2 = disjoint_credit_dti(c2.tp, c2.n_emitted, c2.n_truth)
    assert c2.dti > red2 - 1e-9
    assert exact_dti_from_dot_credits(c2.tp, c2.n_emitted, sum_k2, c2.n_truth) == pytest.approx(c2.dti)


def test_required_recall_and_implied_truth_size_roundtrip():
    for s in (0.26, 0.2778, 0.3195, 0.3345):
        for rho in (0.0, 0.5, 1.0, 2.0):
            x = required_recall(s, rho)
            # rebuild the index from x and rho and confirm it returns s
            G = 10000.0
            T, F = x * G, rho * G
            assert dti_from_components(T, F, G - T) == pytest.approx(s, rel=1e-9)
    # GEMSDOE32's live-anchor inversion: TP_w = 5073.3, D = 18734.4, |G| = 12226
    assert implied_truth_size(5073.3, 18734.4 - 0.2 * 5073.3 - 0.8 * 12226 + 0.2 * 5073.3,
                              0.2708) > 0  # smoke: the helper is finite and positive


def test_shift_semantics():
    a = np.arange(9.0).reshape(3, 3)
    b = shift(a, 1, 1)
    assert b[0, 0] == a[1, 1]
    assert b[2, 2] == 0.0


def test_grid_identity_matches_template():
    from gems43.grid import DTYPE, TRANSFORM, SHAPE
    assert SHAPE == (HEIGHT, WIDTH) == (3730, 3292)
    assert DTYPE == "float32"
    assert TRANSFORM == (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    assert EPSG == 32611
