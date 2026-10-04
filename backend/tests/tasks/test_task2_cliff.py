"""TASK 2 acceptance tests. Run:  pytest -m task tests/tasks/test_task2_cliff.py"""

import numpy as np
import pytest

from pitwall.models.tyre_deg import detect_cliff

pytestmark = pytest.mark.task


def stint(cliff_at, n=30, deg=0.05, cliff_rate=0.08, noise=0.08, seed=0):
    rng = np.random.default_rng(seed)
    age = np.arange(1, n + 1, dtype=float)
    t = 80 + deg * age + rng.normal(0, noise, n)
    if cliff_at is not None:
        t += cliff_rate * np.maximum(age - cliff_at, 0) ** 1.5
    return age, t


@pytest.mark.parametrize("cliff_at", [14, 18, 22])
def test_finds_cliff(cliff_at):
    hits = [detect_cliff(*stint(cliff_at, seed=s)) for s in range(10)]
    assert all(h is not None for h in hits)
    assert np.median(np.abs(np.array(hits) - cliff_at)) <= 3  # smooth cliffs bias hinge fits late


def test_linear_stint_has_no_cliff():
    hits = [detect_cliff(*stint(None, seed=s)) for s in range(20)]
    assert sum(h is not None for h in hits) <= 2  # allow a small false-positive rate


def test_short_stint_returns_none():
    assert detect_cliff(*stint(None, n=8)) is None
