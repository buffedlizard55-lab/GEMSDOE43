import numpy as np

from gemsdoe43.surface import empirical_percentile_surface, greedy_pack, geometric_mean


def test_empirical_percentile_surface_masks_and_handles_ties():
    x = np.array([[0, 1, 1], [2, 3, 99]], dtype=np.float32)
    keep = np.array([[1, 1, 1], [1, 1, 0]], dtype=bool)
    out = empirical_percentile_surface(x, keep)
    assert np.allclose(out[keep], [0.0, 0.375, 0.375, 0.75, 1.0])
    assert out[0, 0] == 0.0
    assert out[1, 2] == 0.0


def test_greedy_packing_is_deterministic_and_obeys_spacing():
    score = np.zeros((20, 20), dtype=np.float32)
    score[5, 5] = 1.0
    score[5, 10] = 0.9
    score[15, 15] = 0.8
    allowed = np.ones_like(score, dtype=bool)
    a = greedy_pack(score, allowed, min_sep=4, budget=3, candidate_cap=1000)
    b = greedy_pack(score, allowed, min_sep=4, budget=3, candidate_cap=1000)
    assert np.array_equal(a, b)
    coords = np.argwhere(a)
    assert coords.shape[0] == 3
    for i in range(len(coords)):
        for j in range(i + 1, len(coords)):
            assert np.linalg.norm(coords[i] - coords[j]) >= 4


def test_geometric_mean_is_bounded_and_equal_terms_preserve_value():
    a = np.array([[0.2, 0.7]], dtype=np.float32)
    out = geometric_mean({"a": a}, {"a": 1.0})
    assert out.shape == a.shape
    assert np.all((out > 0) & (out <= 1))
    assert np.allclose(out, 0.05 + 0.95 * a)
