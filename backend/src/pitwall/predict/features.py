"""Pre-race features for finishing-position prediction.

The cardinal rule: a feature for race k may only use information available BEFORE the
lights go out at race k (qualifying of race k is fine; its result is not).

Data: Jolpica results + qualifying [D2]. Leakage: Kaufman et al. (2012) [M14].
"""

import pandas as pd

FORM_WINDOW = 5  # races; a common "recent form" horizon, our choice rather than a fitted value
KEYS = ["year", "round", "driver_id"]


def _rolling_before(values: pd.Series, groups: pd.Series) -> pd.Series:
    """Mean of the previous FORM_WINDOW values within each group, excluding the current row."""
    return values.groupby(groups).transform(
        lambda s: s.shift(1).rolling(FORM_WINDOW, min_periods=1).mean()
    )


def build_features(results: pd.DataFrame) -> pd.DataFrame:
    """Add pre-race features to a results table (output of `fetch_results`).

    Adds driver_form_pos and team_form_pos (mean finishing position over the previous
    FORM_WINDOW races) and driver_track_best (best finish at this circuit in earlier seasons).
    All are NaN when there is no history. Row order and (year, round, driver) identity are kept.
    """
    df = results.sort_values(["year", "round"], kind="stable")

    driver = df[KEYS].copy()
    driver["driver_form_pos"] = _rolling_before(df["position"], df["driver_id"])

    team_keys = ["constructor_id", "year", "round"]
    team = df[[*team_keys, "position"]].groupby(team_keys, as_index=False, sort=False).mean()
    team = team.sort_values(["year", "round"], kind="stable")
    team["team_form_pos"] = _rolling_before(team["position"], team["constructor_id"])

    track_keys = ["driver_id", "circuit_id", "year"]
    track = df[[*track_keys, "position"]].groupby(track_keys, as_index=False).min()
    track = track.sort_values("year")
    track["driver_track_best"] = track.groupby(["driver_id", "circuit_id"])["position"].transform(
        lambda s: s.cummin().shift(1)
    )

    out = results.merge(driver, on=KEYS, how="left")
    out = out.merge(
        team.drop(columns="position"), on=["constructor_id", "year", "round"], how="left"
    )
    return out.merge(
        track.drop(columns="position"), on=["driver_id", "circuit_id", "year"], how="left"
    )
