"""TASK 6 acceptance tests. Run:  pytest -m task tests/tasks/test_task6_windows.py"""

import numpy as np
import pandas as pd
import pytest

from pitwall.dl.stint_dataset import SEQ_FEATURES, make_windows

pytestmark = pytest.mark.task


@pytest.fixture
def stints():
    rows = []
    for sid, n in [("a", 20), ("b", 10), ("c", 5)]:
        for k in range(n):
            row = {f: 0.0 for f in SEQ_FEATURES}
            row.update(stint_id=sid, tyre_life=k + 1, lap_time_delta_s=1000 * (ord(sid) - 96) + k)
            rows.append(row)
    return pd.DataFrame(rows)


def test_shapes_and_dtype(stints):
    X, y = make_windows(stints, context=8, horizon=3)
    # stint a: 20-11+1 = 10 windows, b: 10-11+1 = 0, c: 0
    assert X.shape == (10, 8, len(SEQ_FEATURES))
    assert y.shape == (10, 3)
    assert X.dtype == np.float32 and y.dtype == np.float32


def test_targets_follow_context(stints):
    X, y = make_windows(stints, context=8, horizon=3)
    i = SEQ_FEATURES.index("lap_time_delta_s")
    assert np.allclose(X[0, :, i], 1000 + np.arange(8))
    assert np.allclose(y[0], 1000 + np.arange(8, 11))


def test_never_crosses_stints(stints):
    X, y = make_windows(stints, context=4, horizon=2)
    i = SEQ_FEATURES.index("lap_time_delta_s")
    stint_of = lambda v: np.floor(v / 1000)  # noqa: E731
    for xw, yw in zip(X, y, strict=True):
        assert len(set(stint_of(xw[:, i])) | set(stint_of(yw))) == 1
