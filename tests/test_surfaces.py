import unittest

import numpy as np

from gemsdoe43.surfaces import triple_gradient_score


def vertical_step(height=64, width=64, left=0.0, right=1.0):
    field = np.full((height, width), left, dtype=np.float32)
    field[:, width // 2:] = right
    return field


class TripleGradientTests(unittest.TestCase):
    def test_triple_edges_score_above_single_edges(self):
        height = width = 64
        valid = np.ones((height, width), dtype=bool)
        hg = vertical_step(height, width)
        vg = vertical_step(height, width, left=0.0, right=2.0)
        rtp = vertical_step(height, width, left=-1.0, right=1.0)
        triple = triple_gradient_score(hg, vg, rtp, valid)
        flat_single = triple_gradient_score(
            hg, np.zeros_like(vg), np.zeros_like(rtp), valid
        )
        self.assertTrue(np.all(np.isfinite(triple)))
        self.assertGreaterEqual(float(triple.min()), 0.05 - 1e-6)
        self.assertLessEqual(float(triple.max()), 1.0)
        # Center column holds the step: triple response there must clearly lead.
        center = slice(width // 2 - 2, width // 2 + 2)
        self.assertGreater(
            float(triple[:, center].mean()), float(flat_single[:, center].mean()) + 0.15
        )

    def test_masked_cells_receive_zero(self):
        field = vertical_step(40, 40)
        valid = np.ones((40, 40), dtype=bool)
        valid[:, :4] = False
        score = triple_gradient_score(field, field, field, valid)
        self.assertTrue(bool(np.all(score[:, :4] == 0.0)))
        self.assertTrue(bool(np.all(score[:, 4:] >= 0.05 - 1e-6)))

    def test_nonfinite_inputs_are_excluded(self):
        field = vertical_step(32, 32)
        hg = field.copy()
        hg[10, 10] = np.nan
        valid = np.ones((32, 32), dtype=bool)
        score = triple_gradient_score(hg, field, field, valid)
        self.assertEqual(float(score[10, 10]), 0.0)
        self.assertTrue(bool(np.all(np.isfinite(score))))

    def test_empty_valid_returns_zeros(self):
        field = vertical_step(16, 16)
        score = triple_gradient_score(
            field, field, field, np.zeros((16, 16), dtype=bool)
        )
        self.assertTrue(bool(np.all(score == 0.0)))

    def test_shape_mismatch_raises(self):
        field = vertical_step(16, 16)
        valid = np.ones((16, 16), dtype=bool)
        with self.assertRaises(ValueError):
            triple_gradient_score(field, field[:8, :8], field, valid)


if __name__ == "__main__":
    unittest.main()
