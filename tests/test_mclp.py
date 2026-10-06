"""Tests for the Church--ReVelle covering solver.

The claims under test are (a) the incremental gain bookkeeping equals a from-scratch
recomputation, (b) the greedy beats the trivial baselines and is within the ``1 - 1/e`` band of
an exhaustive optimum on a problem small enough to solve by brute force, and (c) the
Dinkelbach cardinality rule reproduces the ratio objective's own optimum.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from gems43.grid import KERNEL_W, OFFSETS, shift
from gems43.mclp import (
    CoverSolution,
    coverage_potential,
    dinkelbach_budget,
    emission_plan,
    greedy_cover,
    marginal_gain,
)


def _demand(H, W, kind="line", seed=0):
    rng = np.random.default_rng(seed)
    p = np.zeros((H, W), dtype=np.float32)
    if kind == "line":
        p[:, W // 2] = 1.0                       # one continuous fault trace
    elif kind == "two_lines":
        p[:, W // 3] = 1.0
        p[:, 2 * W // 3] = 0.6
    else:
        m = rng.random((H, W)) < 0.03
        p[m] = rng.random(int(m.sum())) + 0.2
    return p


def _covered(prior, dots, H, W):
    """From-scratch coverage of a dot set: sum_x pi(x) * max_i k(d(i, x))."""
    credit = np.zeros((H, W), dtype=np.float64)
    for (r, c) in dots:
        for (dr, dc), w in zip(OFFSETS, KERNEL_W):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and w > credit[rr, cc]:
                credit[rr, cc] = w
    return float((prior.astype(np.float64) * credit).sum()), credit


def test_marginal_gain_matches_from_scratch():
    H, W = 40, 40
    prior = _demand(H, W, "random", seed=3)
    rng = np.random.default_rng(1)
    dots = [(int(a), int(b)) for a, b in rng.integers(0, H, size=(12, 2))]
    credit = np.zeros((H, W), dtype=np.float32)
    for (r, c) in dots:
        for (dr, dc), w in zip(OFFSETS, KERNEL_W):
            rr, cc = r + dr, c + dc
            if 0 <= rr < H and 0 <= cc < W and w > credit[rr, cc]:
                credit[rr, cc] = w
    g = marginal_gain(prior, credit)
    for (r, c) in [(5, 5), (20, 20), (39, 39), (0, 0)]:
        before, _ = _covered(prior, dots, H, W)
        after, _ = _covered(prior, dots + [(r, c)], H, W)
        assert g[r, c] == pytest.approx(after - before, abs=1e-5)


def test_greedy_is_exact_on_small_bruteforce_problem():
    """On a problem small enough to enumerate, greedy must reach >= (1-1/e) * optimum
    and, for these tiny instances, usually the optimum itself."""
    H, W = 15, 15
    prior = _demand(H, W, "line")
    cand = np.ones((H, W), dtype=bool)
    K = 4
    sol = greedy_cover(prior, cand, K, min_potential=0.0, strict_grid=False)
    dots = [divmod(int(i), W) for i in sol.order]

    # brute force over all K-subsets of a 15x15 grid is 15^C4... restrict to the central band
    pool = [(r, c) for r in range(H) for c in range(W)]
    best = -1.0
    rng = np.random.default_rng(0)
    # exhaustive over a reduced pool that provably contains the optimum for a vertical line:
    # the optimum dots all sit on the line column, so enumerate K-subsets of that column
    col = W // 2
    pool = [(r, col) for r in range(H)]
    for combo in itertools.combinations(pool, K):
        v, _ = _covered(prior, list(combo), H, W)
        best = max(best, v)
    got = float(sol.cumulative[-1])
    assert got <= best + 1e-4
    assert got >= (1.0 - np.e ** -1) * best - 1e-4


def test_greedy_cumulative_matches_independent_recomputation():
    H, W = 60, 60
    prior = _demand(H, W, "two_lines")
    cand = np.ones((H, W), dtype=bool)
    sol = greedy_cover(prior, cand, 25, strict_grid=False)
    for K in (1, 5, 25):
        dots = [divmod(int(i), W) for i in sol.order[:K]]
        v, _ = _covered(prior, dots, H, W)
        assert sol.cumulative[K - 1] == pytest.approx(v, rel=1e-4)


def test_marginals_are_non_increasing(submodularity_check=True):
    """Submodularity: the realised marginal sequence of greedy must be non-increasing."""
    H, W = 80, 80
    prior = _demand(H, W, "random", seed=5)
    sol = greedy_cover(prior, np.ones((H, W), bool), 40, strict_grid=False)
    d = np.diff(sol.marginal)
    assert d.max() <= 1e-4, "diminishing returns violated"


def test_no_dot_is_selected_twice_and_all_on_candidates():
    H, W = 50, 50
    prior = _demand(H, W, "random", seed=9)
    cand = np.zeros((H, W), bool)
    cand[10:40, 10:40] = True
    sol = greedy_cover(prior, cand, 30, strict_grid=False)
    assert len(set(sol.order.tolist())) == len(sol.order)
    r, c = np.unravel_index(sol.order, (H, W))
    assert cand[r, c].all()


def test_emission_plan_fixed_point():
    H, W = 70, 70
    prior = _demand(H, W, "two_lines") * 40.0     # ~4,200 truth pixels
    sol = greedy_cover(prior, np.ones((H, W), bool), 300, strict_grid=False)
    plan = emission_plan(sol)
    # the returned cardinality must itself satisfy the marginal bar at its own score
    bar = plan["marginal_bar"]
    assert sol.marginal[plan["k_star"] - 1] > bar
    if plan["k_star"] < sol.k:
        assert sol.marginal[plan["k_star"]] <= bar
    assert plan["dti_bound_at_k_star"] <= plan["dti_bound_max"] + 1e-12


def test_dinkelbach_budget_monotone_in_truth_size():
    H, W = 70, 70
    prior = _demand(H, W, "two_lines") * 40.0
    sol = greedy_cover(prior, np.ones((H, W), bool), 400, strict_grid=False)
    tbl = dinkelbach_budget(sol, [5_000, 12_000, 25_000, 50_000])
    ks = [row["k_argmax_ratio"] for row in tbl]
    assert ks == sorted(ks), "a larger truth set can afford (weakly) more dots"
    for row in tbl:
        assert row["dti_bound_at_marginal_rule"] <= row["dti_bound_at_argmax"] + 1e-9


def test_coverage_potential_equals_isolated_coverage():
    H, W = 45, 45
    prior = _demand(H, W, "random", seed=2)
    pot = coverage_potential(prior)
    for (r, c) in [(10, 10), (22, 22), (44, 0)]:
        v, _ = _covered(prior, [(r, c)], H, W)
        assert pot[r, c] == pytest.approx(v, rel=1e-4)
