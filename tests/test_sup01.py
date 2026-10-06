import unittest

import numpy as np

from gemsdoe43.sup01 import HGB_PARAMS, fit_predict_in_sample, train_predict_proba


class Sup01Tests(unittest.TestCase):
    def test_in_sample_helper_matches_indexed_helper(self):
        rng = np.random.default_rng(20261006)
        stack = rng.normal(size=(800, 6)).astype(np.float32)
        labels = (rng.random(800) < 0.1).astype(np.int8)
        train_flat = np.arange(600)
        proba_indexed, info_indexed = train_predict_proba(
            stack, train_flat, labels[train_flat], train_flat)
        proba_direct, info_direct = fit_predict_in_sample(
            np.ascontiguousarray(stack[train_flat]), labels[train_flat])
        np.testing.assert_allclose(proba_direct, proba_indexed, rtol=0, atol=0)
        self.assertEqual(info_direct["n_train"], info_indexed["n_train"])
        self.assertEqual(info_direct["n_train_positive"], info_indexed["n_train_positive"])
        self.assertEqual(info_direct["n_iter"], info_indexed["n_iter"])
        self.assertTrue(bool(np.all(proba_direct >= 0.0)))
        self.assertTrue(bool(np.all(proba_direct <= 1.0)))

    def test_frozen_hyperparameters(self):
        self.assertEqual(HGB_PARAMS["random_state"], 20261006)
        self.assertEqual(HGB_PARAMS["class_weight"], "balanced")
        self.assertTrue(HGB_PARAMS["early_stopping"])
        for key in ("max_iter", "learning_rate", "max_leaf_nodes",
                    "min_samples_leaf", "l2_regularization",
                    "validation_fraction", "n_iter_no_change"):
            self.assertIn(key, HGB_PARAMS)


if __name__ == "__main__":
    unittest.main()
