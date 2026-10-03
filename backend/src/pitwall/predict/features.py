"""Pre-race features for finishing-position prediction — TASK 5 (docs/tasks/05-race-predictor.md).

The cardinal rule: a feature for race k may only use information available BEFORE the
lights go out at race k (qualifying of race k is fine; its result is not).

Data: Jolpica results + qualifying [D2]. Leakage: Kaufman et al. (2012) [M14].
"""

from __future__ import annotations

import pandas as pd


def build_features(results: pd.DataFrame) -> pd.DataFrame:
    """Add pre-race features to a results table (output of `fetch_results`).

    Required output columns (add more!):
        grid                       starting position (already in the input)
        driver_form_pos            driver's mean finishing position over their previous 5 races
        team_form_pos              team's mean finishing position over its previous 5 races
        driver_track_best          best finish at this circuit in earlier seasons (NaN if none)

    Rows must keep their (year, round, driver) identity and order.
    """
    raise NotImplementedError("TASK 5 — see docs/tasks/05-race-predictor.md")
