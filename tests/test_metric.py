import numpy as np

from gemsdoe43.metric import dti, dti_bruteforce


def test_distance_weighted_tversky_matches_independent_small_array_oracle():
    rng = np.random.default_rng(43)
    truth = rng.random((17, 19)) < 0.06
    pred = np.zeros((17, 19), dtype=np.float32)
    emit = rng.random(pred.shape) < 0.05
    pred[emit] = rng.uniform(0.2, 1.0, size=int(emit.sum()))
    foot = rng.random(pred.shape) > 0.1
    a = dti(pred, truth, foot)
    b = dti_bruteforce(pred, truth, foot)
    for key in ("tp", "fp", "fn", "mass", "dti"):
        assert np.isclose(a[key], b[key], rtol=1e-11, atol=1e-11), key


def test_masked_cells_do_not_contribute():
    truth = np.zeros((12, 12), dtype=bool)
    truth[5, 5] = True
    pred = np.zeros((12, 12), dtype=np.float32)
    pred[5, 5] = 1.0
    pred[0, 0] = 1.0
    footprint = np.zeros_like(truth)
    footprint[4:8, 4:8] = True
    result = dti(pred, truth, footprint)
    assert result["mass"] == 1.0
    assert result["tp"] == 1.0
    assert result["fp"] == 0.0
    assert result["dti"] > 0.999999
