"""TASK 3 acceptance tests — run:  pytest -m task tests/tasks/test_task3_splits.py"""

import numpy as np
import pandas as pd
import pytest

from pitwall.models.pace_gbm import time_series_splits

pytestmark = pytest.mark.task


@pytest.fixture
def df():
    rows = [(y, r, i) for y in (2023, 2024) for r in range(1, 23) for i in range(50)]
    out = pd.DataFrame(rows, columns=["year", "round", "i"])
    return out.sample(frac=1, random_state=0).reset_index(drop=True)  # shuffled on purpose


def test_test_races_strictly_after_train_races(df):
    splits = list(time_series_splits(df, n_splits=4))
    assert len(splits) == 4
    key = df["year"] * 100 + df["round"]
    for train_idx, test_idx in splits:
        assert len(train_idx) and len(test_idx)
        assert key.iloc[train_idx].max() < key.iloc[test_idx].min()


def test_a_race_is_never_split(df):
    key = df["year"] * 100 + df["round"]
    for train_idx, test_idx in time_series_splits(df, n_splits=4):
        assert not set(key.iloc[train_idx]) & set(key.iloc[test_idx])


def test_training_window_grows(df):
    sizes = [len(tr) for tr, _ in time_series_splits(df, n_splits=4)]
    assert np.all(np.diff(sizes) > 0)
