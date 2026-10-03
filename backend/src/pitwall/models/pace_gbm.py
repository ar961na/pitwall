"""Gradient-boosted pace model across many races — TASK 3 (docs/tasks/03-pace-model-gbm.md).

References: LightGBM [M9], quantile loss [M10], Huber loss [M11], time-ordered CV [M13].
"""

from __future__ import annotations

import pandas as pd

FEATURES = [
    # Start with these, then add your own (track temp, circuit, team, laps_remaining, ...)
    "compound",
    "tyre_life",
    "lap",
    "laps_remaining",
    "stint",
]
# lap time minus the driver's median in that race: removes car pace and circuit length
TARGET = "lap_time_delta_s"


def build_pace_dataset(years: list[int]) -> pd.DataFrame:
    """Green-flag laps from every race in `years`, with the target column added."""
    raise NotImplementedError("TASK 3 — see docs/tasks/03-pace-model-gbm.md")


def time_series_splits(df: pd.DataFrame, n_splits: int = 4):
    """Yield (train_idx, test_idx) where every test race happens AFTER every train race."""
    raise NotImplementedError("TASK 3 — see docs/tasks/03-pace-model-gbm.md")
