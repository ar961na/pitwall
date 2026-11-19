"""Sequence dataset of stints for lap-time forecasting.

Idea: given the last `context` laps of a stint (lap-time deltas + features), predict the next
`horizon` lap-time deltas. A sequence model can learn non-linear wear (the cliff) and
driver-specific management that the linear/GBM models can't see.

References: LSTM/GRU [M24], Transformer [M25], time-ordered splits [M13].
"""

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

SEQ_FEATURES = [
    "lap_time_delta_s",
    "tyre_life",
    "laps_remaining",
    "compound_soft",
    "compound_medium",
    "compound_hard",
]


def make_windows(
    stints: pd.DataFrame, context: int = 8, horizon: int = 3
) -> tuple[np.ndarray, np.ndarray]:
    """Sliding windows within each stint: `context` laps of features, next `horizon` targets.

    `stints` needs `stint_id` and every column in SEQ_FEATURES, sorted by lap within stint.
    Returns float32 X (n_windows, context, n_features) and y (n_windows, horizon) of future
    `lap_time_delta_s`. Windows never cross stints; short stints yield nothing.
    """
    size = context + horizon
    target = SEQ_FEATURES.index("lap_time_delta_s")
    xs, ys = [], []
    for _, stint in stints.groupby("stint_id", sort=False):
        values = stint[SEQ_FEATURES].to_numpy(np.float32)
        if len(values) < size:
            continue
        # (n_windows, size, n_features)
        windows = sliding_window_view(values, size, axis=0).transpose(0, 2, 1)
        xs.append(windows[:, :context, :])
        ys.append(windows[:, context:, target])
    if not xs:
        return (
            np.zeros((0, context, len(SEQ_FEATURES)), np.float32),
            np.zeros((0, horizon), np.float32),
        )
    return np.concatenate(xs), np.concatenate(ys)
