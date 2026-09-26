import numpy as np
import pytest

from refitt_host.astro_prost_math import score_offset_samples


def test_vectorized_offset_scores_normalize_each_draw():
    score = score_offset_samples(
        np.array([10.0, 10.01]), np.array([0.0, 0.0]),
        np.array([10.0, 10.0]), np.array([0.0, 0.0]),
        np.ones((2, 2)), np.ones((2, 2)), np.zeros((2, 2)),
    )
    total = score.probabilities.sum(axis=0) + sum(score.nulls.values())
    assert np.allclose(total, 1.0)


def test_vectorized_offset_rejects_mismatched_sample_shapes():
    with pytest.raises(ValueError, match="ellipse"):
        score_offset_samples(
            np.array([10.0]), np.array([0.0]), np.array([10.0]), np.array([0.0]),
            np.ones((1, 1)), np.ones((1, 2)), np.zeros((1, 1)),
        )
