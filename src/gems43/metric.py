"""The official distance-weighted Tversky index (DW-Tversky), implemented verbatim.

Source (read 2026-10-06):
<https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/> , section
"Performance metric".  With p(x) in [0,1] the predicted probability and g the ground truth set:

    k(d)   = max(1 - d/R, 0),                 R = 300 m
    TP_w   = sum_{g in G} max_{x: d(x,g) <= R} p(x) * k(d(x,g))
    FP_w   = sum_{x: p(x) > 0} p(x) * [1 - max_{g in G} k(d(x,g))]
    FN_w   = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) * k(d(x,g))]
    DTI    = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps),   alpha = 0.2, beta = 0.8

Three consequences, all used elsewhere in this package, are proved in
``docs/research/metric-algebra.md`` and unit-tested in ``tests/test_metric.py``:

1. ``FN_w = |G| - TP_w`` exactly, so ``DTI = T / (0.2*T + 0.2*F + 0.8*|G|)``.
2. Adding a pixel of weight ``p`` whose best kernel credit is ``k`` raises the denominator by
   exactly ``0.2*p`` regardless of ``k``; the move therefore pays iff ``k > 0.2*DTI``, and the
   marginal rule is independent of ``p``.  Binary (p = 1) emission is optimal.
3. For a **binary** emission ``F(S) = |S| - sum_i k_i`` with ``k_i = max_g k(d(i,g))`` a modular
   function of S.  Under the *disjoint-credit hypothesis* -- each dot is credited against a
   distinct truth pixel, i.e. ``sum_i k_i = T`` -- the index reduces to

       DTI_red = T / (0.2*|S| + 0.8*|G|)                                          (reduction)

   so that for a **fixed** number of dots ``|S| = K`` the placement problem is *exactly* the
   Church--ReVelle maximal covering location problem.

   The reduction is a *hypothesis*, not a bound, and the sign of its error is known:
   ``DTI = T / (0.2T + 0.2(|S| - sum_i k_i) + 0.8|G|)``, so ``sum_i k_i > T`` (several dots
   competing for the same truth pixel -- the regime at K > |G|) makes the reduction
   **pessimistic**, and ``sum_i k_i < T`` (fewer dots than truth pixels) makes it
   **optimistic**.  Reported as ``disjoint_credit_dti`` and always labelled as the reduction.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .grid import ALPHA, BETA, EPS, KERNEL_W, OFFSETS, R_PIXELS, shift

__all__ = ["dti_components", "dti", "disjoint_credit_dti", "marginal_threshold",
           "dti_from_components", "exact_dti_from_dot_credits"]


def _best_kernel_credit(source: np.ndarray) -> np.ndarray:
    """``M[x] = max_{g in source} k(d(x, g))`` — grey dilation of ``source`` by the kernel.

    ``source`` may be a boolean truth mask or a non-negative weight field.  For a boolean
    mask this is exactly ``max_{g in G} k(d(x,g))`` as the official page defines it.
    """
    out = np.zeros(source.shape, dtype=np.float64)
    src = source.astype(np.float64, copy=False)
    for (dr, dc), w in zip(OFFSETS, KERNEL_W):
        if w <= 0.0:
            continue
        np.maximum(out, w * shift(src, -dr, -dc), out=out)
    return out


@dataclass
class Components:
    """The three weighted counts of the official metric."""

    tp: float
    fp: float
    fn: float
    n_truth: int
    n_emitted: int

    @property
    def dti(self) -> float:
        return dti_from_components(self.tp, self.fp, self.fn)

    @property
    def weighted_recall(self) -> float:
        return self.tp / self.n_truth if self.n_truth else 0.0

    @property
    def denominator(self) -> float:
        return self.tp + ALPHA * self.fp + BETA * self.fn


def dti_components(pred: np.ndarray, truth: np.ndarray) -> Components:
    """Exact TP_w / FP_w / FN_w for a prediction field against a truth mask.

    Parameters
    ----------
    pred : (H, W) float array of predicted probabilities in [0, 1]; anything <= 0 is "no call".
    truth : (H, W) boolean array of ground-truth fault pixels.
    """
    pred = np.asarray(pred, dtype=np.float64)
    truth = np.asarray(truth, dtype=bool)

    # --- TP_w : for each truth pixel, the best weighted credit offered by any prediction.
    best_credit = np.zeros(pred.shape, dtype=np.float64)
    for (dr, dc), w in zip(OFFSETS, KERNEL_W):
        if w <= 0.0:
            continue
        # credit offered at pixel g by the prediction placed at g + (dr, dc)
        np.maximum(best_credit, w * shift(pred, dr, dc), out=best_credit)
    tp = float(best_credit[truth].sum())

    # --- FP_w : for each called pixel, p(x) * (1 - max_g k(d(x,g)))
    truth_kernel = _best_kernel_credit(truth)
    called = pred > 0
    fp = float((pred[called] * (1.0 - truth_kernel[called])).sum())

    n_truth = int(truth.sum())
    fn = float(n_truth - tp)                      # consequence (1)
    return Components(tp=tp, fp=fp, fn=fn, n_truth=n_truth, n_emitted=int(called.sum()))


def dti_from_components(tp: float, fp: float, fn: float) -> float:
    """``DTI = TP / (TP + alpha*FP + beta*FN + eps)``."""
    den = tp + ALPHA * fp + BETA * fn + EPS
    return float(tp / den) if den > 0 else 0.0


def dti(pred: np.ndarray, truth: np.ndarray) -> float:
    """Scalar DW-Tversky index of a prediction field against a truth mask."""
    return dti_components(pred, truth).dti


def disjoint_credit_dti(tp: float, n_emitted: int, n_truth: int) -> float:
    """Consequence (3), **reduction not bound**: ``T / (0.2*|S| + 0.8*|G|)``.

    Equals the true index iff each emitted dot is credited against a distinct truth pixel.
    See the module docstring for the sign of the error in each regime.
    """
    return float(tp / (ALPHA * n_emitted + BETA * n_truth + EPS))


def exact_dti_from_dot_credits(tp: float, n_emitted: int, sum_dot_credits: float,
                               n_truth: int) -> float:
    """Exact index for a binary emission given ``sum_i k_i``: no hypothesis required.

    ``F = |S| - sum_i k_i`` exactly, so
    ``DTI = T / (0.2*T + 0.2*(|S| - sum_i k_i) + 0.8*|G|)``.
    """
    den = ALPHA * tp + ALPHA * (n_emitted - sum_dot_credits) + BETA * n_truth + EPS
    return float(tp / den) if den > 0 else 0.0


def marginal_threshold(score: float) -> float:
    """Consequence (2): a pixel pays for itself iff its kernel credit exceeds ``0.2 * s``."""
    return ALPHA * score


def required_recall(score: float, fp_per_truth: float = 0.0) -> float:
    """Weighted recall ``T/|G|`` needed to reach ``score`` at false-positive ratio ``F/|G|``.

    Inverting ``s = T / (0.2T + 0.2F + 0.8G)`` with ``rho = F/G`` gives
    ``T/G = s*(0.2*rho + 0.8) / (1 - 0.2*s)``.
    """
    return score * (ALPHA * fp_per_truth + BETA) / (1.0 - ALPHA * score)


def implied_truth_size(tp: float, fp: float, score: float) -> float:
    """Invert the index for ``|G|`` given the weighted counts and the observed score."""
    return (tp * (1.0 - ALPHA * score) - ALPHA * score * fp) / (BETA * score)
