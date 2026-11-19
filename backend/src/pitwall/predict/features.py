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

    Adds quali_gap_pct (best qualifying lap vs the fastest, in percent), grid_eff (grid with
    pit-lane starts moved to the back), season points before the race for driver and team,
    driver_form_pos and team_form_pos (mean finishing position over the previous
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

    season = ["driver_id", "year"]
    driver["driver_points_before"] = df.groupby(season)["points"].transform(
        lambda s: s.cumsum().shift(1).fillna(0.0)
    )
    team_points = df[[*team_keys, "points"]].groupby(team_keys, as_index=False, sort=False).sum()
    team_points["team_points_before"] = team_points.groupby(["constructor_id", "year"])[
        "points"
    ].transform(lambda s: s.cumsum().shift(1).fillna(0.0))
    team = team.merge(team_points.drop(columns="points"), on=team_keys)

    race = [df["year"], df["round"]]
    best_lap = df[["q1_s", "q2_s", "q3_s"]].min(axis=1)
    driver["quali_gap_pct"] = (best_lap / best_lap.groupby(race).transform("min") - 1) * 100
    field = df.groupby(race)["driver_id"].transform("size")
    # Jolpica codes a pit-lane start as grid 0; it is effectively last
    driver["grid_eff"] = df["grid"].where(df["grid"] > 0, field)

    out = results.merge(driver, on=KEYS, how="left")
    out = out.merge(
        team.drop(columns="position"), on=["constructor_id", "year", "round"], how="left"
    )
    return out.merge(
        track.drop(columns="position"), on=["driver_id", "circuit_id", "year"], how="left"
    )
