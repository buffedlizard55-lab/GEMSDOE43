import itertools
import unittest

import numpy as np

from gemsdoe43.mclp import (
    PAD,
    coverage_objective,
    initial_gains,
    lazy_greedy_cover,
    triangular_kernel_2d,
)


def brute_force_optimum(demand, eligible, budget):
    """Exact optimum by enumeration; only for tiny grids in tests."""
    demand = np.asarray(demand, dtype=np.float64)
    eligible = np.asarray(eligible, dtype=bool)
    cells = np.flatnonzero(eligible.ravel())
    best_value = -1.0
    best_set = None
    height, width = demand.shape
    for combo in itertools.combinations(cells.tolist(), budget):
        mask = np.zeros(demand.shape, dtype=bool)
        mask.ravel()[list(combo)] = True
        value = coverage_objective(mask, demand)
        if value > best_value:
            best_value = value
            best_set = set(combo)
    return best_value, best_set


class KernelTests(unittest.TestCase):
    def test_kernel_shape_weights_and_support(self):
        kernel = triangular_kernel_2d()
        self.assertEqual(kernel.shape, (7, 7))
        self.assertAlmostEqual(float(kernel[3, 3]), 1.0)
        self.assertAlmostEqual(float(kernel[3, 4]), 2.0 / 3.0)
        self.assertAlmostEqual(float(kernel[3, 5]), 1.0 / 3.0)
        self.assertAlmostEqual(float(kernel[3, 6]), 0.0)
        # Diagonal at distance sqrt(8): 1 - sqrt(8)/3.
        self.assertAlmostEqual(float(kernel[1, 1]), 1.0 - np.hypot(2, 2) / 3.0)
        # Symmetric, nonnegative, bounded by 1.
        np.testing.assert_allclose(kernel, kernel[::-1, ::-1])
        self.assertTrue(bool(np.all(kernel >= 0.0)))
        self.assertTrue(bool(np.all(kernel <= 1.0)))

    def test_initial_gains_match_direct_objective_for_singletons(self):
        rng = np.random.default_rng(20261006)
        demand = rng.random((9, 11)).astype(np.float64)
        eligible = np.ones_like(demand, dtype=bool)
        eligible[0, 0] = False
        gains = initial_gains(demand, eligible)
        self.assertTrue(np.isneginf(gains[0, 0]))
        for flat in (5, 40, 90):
            mask = np.zeros_like(eligible)
            mask.ravel()[flat] = True
            self.assertAlmostEqual(
                float(gains.ravel()[flat]), coverage_objective(mask, demand), places=9
            )


class LazyGreedyTests(unittest.TestCase):
    def test_single_unit_demand_selects_its_own_cell(self):
        demand = np.zeros((11, 13), dtype=np.float64)
        demand[5, 6] = 1.0
        eligible = np.ones_like(demand, dtype=bool)
        selected, stats = lazy_greedy_cover(demand, eligible, budget=1)
        self.assertEqual(int(selected.sum()), 1)
        self.assertTrue(selected[5, 6])
        self.assertAlmostEqual(stats["objective"], 1.0)

    def test_separated_unit_demands_are_all_selected(self):
        demand = np.zeros((21, 21), dtype=np.float64)
        points = [(3, 3), (3, 17), (17, 3), (17, 17)]
        for row, col in points:
            demand[row, col] = 1.0
        eligible = np.ones_like(demand, dtype=bool)
        selected, stats = lazy_greedy_cover(demand, eligible, budget=4)
        for row, col in points:
            self.assertTrue(selected[row, col], f"missed {(row, col)}")
        self.assertAlmostEqual(stats["objective"], 4.0)

    def test_deterministic_tie_break_on_uniform_demand(self):
        demand = np.full((15, 15), 0.25, dtype=np.float64)
        eligible = np.ones_like(demand, dtype=bool)
        first, _ = lazy_greedy_cover(demand, eligible, budget=6)
        second, _ = lazy_greedy_cover(demand, eligible, budget=6)
        np.testing.assert_array_equal(first, second)
        self.assertEqual(int(first.sum()), 6)

    def test_greedy_meets_one_minus_one_over_e_on_tiny_grids(self):
        rng = np.random.default_rng(777)
        for trial in range(6):
            demand = rng.random((6, 6)).astype(np.float64)
            eligible = np.ones((6, 6), dtype=bool)
            optimum, _ = brute_force_optimum(demand, eligible, budget=3)
            selected, stats = lazy_greedy_cover(
                demand, eligible, budget=3, candidate_cap=36
            )
            self.assertEqual(int(selected.sum()), 3)
            self.assertAlmostEqual(
                stats["objective"], coverage_objective(selected, demand), places=9
            )
            self.assertGreaterEqual(stats["objective"], (1.0 - 1.0 / np.e) * optimum - 1e-9)

    def test_candidate_cap_restricts_selection_pool(self):
        rng = np.random.default_rng(4242)
        demand = rng.random((20, 20)).astype(np.float64)
        eligible = np.ones_like(demand, dtype=bool)
        selected, stats = lazy_greedy_cover(
            demand, eligible, budget=10, candidate_cap=50
        )
        self.assertEqual(stats["candidates"], 50)
        gains0 = initial_gains(demand, eligible)
        order = np.lexsort(
            (np.arange(demand.size), -gains0.ravel())
        )[:50]
        allowed = set(order.tolist())
        chosen = set(np.flatnonzero(selected.ravel()).tolist())
        self.assertTrue(chosen.issubset(allowed))

    def test_ineligible_cells_are_never_selected(self):
        rng = np.random.default_rng(99)
        demand = rng.random((14, 12)).astype(np.float64)
        eligible = rng.random((14, 12)) > 0.4
        selected, stats = lazy_greedy_cover(demand, eligible, budget=25)
        self.assertTrue(bool(np.all(selected[~eligible] == False)))
        self.assertEqual(int(selected.sum()), min(25, int(eligible.sum())))

    def test_recompute_guard_aborts_without_partial_state(self):
        demand = np.full((30, 30), 0.5, dtype=np.float64)
        eligible = np.ones_like(demand, dtype=bool)
        with self.assertRaises(RuntimeError):
            lazy_greedy_cover(demand, eligible, budget=100, max_recomputes=5)

    def test_zero_budget_selects_nothing(self):
        demand = np.ones((5, 5), dtype=np.float64)
        eligible = np.ones_like(demand, dtype=bool)
        selected, stats = lazy_greedy_cover(demand, eligible, budget=0)
        self.assertEqual(int(selected.sum()), 0)
        self.assertEqual(stats["objective"], 0.0)


if __name__ == "__main__":
    unittest.main()
