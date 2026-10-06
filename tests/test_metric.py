import unittest

import numpy as np

from gemsdoe43.metric import dti, dti_bruteforce, kernel


class MetricTests(unittest.TestCase):
    def test_kernel_is_triangular_at_100m_grid_cells(self):
        np.testing.assert_allclose(kernel([0.0, 1.0, 2.0, 3.0, 4.0]), [1.0, 2 / 3, 1 / 3, 0.0, 0.0])

    def test_fast_implementation_matches_direct_formula_with_fractional_mass(self):
        rng = np.random.default_rng(20261006)
        for _ in range(30):
            truth = rng.random((11, 13)) < 0.08
            prediction = rng.random((11, 13))
            prediction[prediction < 0.78] = 0.0
            prediction[0, 0] = np.nan
            footprint = rng.random((11, 13)) > 0.12
            known = rng.random((11, 13)) < 0.04
            actual = dti(prediction, truth, footprint, known)
            expected = dti_bruteforce(prediction, truth, footprint, known)
            for key in ("tp", "fp", "fn", "dti", "mass", "credit_per_mass"):
                self.assertAlmostEqual(actual[key], expected[key], places=11, msg=key)
            self.assertEqual(actual["n_truth"], expected["n_truth"])

    def test_known_pixels_are_excluded_from_both_truth_and_prediction(self):
        truth = np.zeros((9, 9), dtype=bool)
        truth[4, 4] = True
        truth[4, 7] = True
        pred = np.zeros((9, 9), dtype=float)
        pred[4, 4] = 1.0
        pred[4, 7] = 1.0
        known = np.zeros_like(truth)
        known[4, 4] = True
        result = dti(pred, truth, known=known)
        self.assertEqual(result["n_truth"], 1)
        self.assertAlmostEqual(result["tp"], 1.0)
        self.assertAlmostEqual(result["fp"], 0.0)
        self.assertAlmostEqual(result["dti"], 1.0)

    def test_three_pixel_distance_has_zero_kernel_credit(self):
        truth = np.zeros((9, 9), dtype=bool)
        truth[4, 4] = True
        pred = np.zeros((9, 9), dtype=float)
        pred[4, 7] = 1.0
        result = dti(pred, truth)
        self.assertAlmostEqual(result["tp"], 0.0)
        self.assertAlmostEqual(result["fp"], 1.0)
        self.assertAlmostEqual(result["fn"], 1.0)

    def test_empty_truth_has_zero_score_and_all_mass_false_positive(self):
        truth = np.zeros((4, 5), dtype=bool)
        pred = np.full((4, 5), 0.25, dtype=float)
        result = dti(pred, truth)
        self.assertEqual(result["n_truth"], 0)
        self.assertEqual(result["tp"], 0.0)
        self.assertAlmostEqual(result["fp"], 5.0)
        self.assertEqual(result["dti"], 0.0)


if __name__ == "__main__":
    unittest.main()
