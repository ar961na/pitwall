"""Sequence dataset of stints for lap-time forecasting (TASK 6, docs/tasks/06-sequence-model.md).

Idea: given the last `context` laps of a stint (lap-time deltas + features), predict the next
`horizon` lap-time deltas. A sequence model can learn non-linear wear (the cliff) and
driver-specific management that the linear/GBM models can't see.

References: LSTM/GRU [M24], Transformer [M25], time-ordered splits [M13].
"""

import numpy as np
import pandas as pd

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
    """Slide a window over every stint.

    Args:
        stints: green-flag laps with a stint id column `stint_id`, sorted by lap within stint,
            containing every column in SEQ_FEATURES.
        context: number of past laps the model sees.
        horizon: number of future lap-time deltas to predict.

    Returns:
        X: float32 array (n_windows, context, len(SEQ_FEATURES))
        y: float32 array (n_windows, horizon): future `lap_time_delta_s`
        Windows never cross stint boundaries; stints shorter than context + horizon yield nothing.
    """
    raise NotImplementedError("TASK 6: see docs/tasks/06-sequence-model.md")
