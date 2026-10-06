import unittest

import numpy as np

from gemsdoe43.cg01 import cross_gradient_score
from gemsdoe43.density import greedy_pack, norm01


class DensityTests(unittest.TestCase):
    def test_greedy_pack_obeys_budget_and_minimum_distance(self):
        score = np.arange(30 * 30, dtype=np.float32).reshape(30, 30)
        allowed = np.ones(score.shape, dtype=bool)
        selected = greedy_pack(score, allowed, min_sep=4.0, budget=20)
        self.assertEqual(int(selected.sum()), 20)
        rows, cols = np.nonzero(selected)
        for i in range(len(rows)):
            distances = np.hypot(rows[i + 1:] - rows[i], cols[i + 1:] - cols[i])
            self.assertTrue(np.all(distances > 4.0))

    def test_normalization_ignores_invalid_cells(self):
        values = np.array([[0.0, 1.0], [2.0, 1000.0]], dtype=np.float32)
        keep = np.array([[True, True], [True, False]])
        out = norm01(values, keep, high_percentile=100.0)
        self.assertEqual(float(out[1, 1]), 0.0)
        self.assertEqual(float(out[1, 0]), 1.0)


class CrossGradientTests(unittest.TestCase):
    def test_parallel_and_antiparallel_edges_score_above_orthogonal_edges(self):
        height = width = 96
        magnetic = np.zeros((height, width), dtype=np.float32)
        magnetic[:, width // 2:] = 1.0
        gravity_parallel = np.zeros_like(magnetic)
        gravity_parallel[:, width // 2:] = -3.0
        gravity_orthogonal = np.zeros_like(magnetic)
        gravity_orthogonal[height // 2:, :] = 2.0
        valid = np.ones_like(magnetic, dtype=bool)
        parallel = cross_gradient_score(magnetic, gravity_parallel, valid)
        orthogonal = cross_gradient_score(magnetic, gravity_orthogonal, valid)
        self.assertTrue(np.all(np.isfinite(parallel)))
        self.assertGreater(float(parallel.max()), float(orthogonal.max()) + 0.2)
        self.assertLessEqual(float(parallel.max()), 1.0)

    def test_masked_outside_cells_do_not_receive_scores(self):
        magnetic = np.zeros((40, 40), dtype=np.float32)
        gravity = np.zeros_like(magnetic)
        magnetic[:, 20:] = 1.0
        gravity[:, 20:] = 1.0
        valid = np.ones_like(magnetic, dtype=bool)
        valid[:, :3] = False
        score = cross_gradient_score(magnetic, gravity, valid)
        self.assertTrue(np.all(score[:, :3] == 0.0))


if __name__ == "__main__":
    unittest.main()
