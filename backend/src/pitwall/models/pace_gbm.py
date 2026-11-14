"""Gradient-boosted pace model across many races.

References: LightGBM [M9], quantile loss [M10], Huber loss [M11], time-ordered CV [M13].
"""

import logging
from collections.abc import Iterator

import numpy as np
import pandas as pd

from pitwall.data import openf1
from pitwall.data.laps import green_flag_laps, race_laps

FEATURES = ["compound", "tyre_life", "lap_frac", "laps_remaining", "stint", "fresh_tyre", "circuit"]
CATEGORICAL = ["compound", "circuit"]
# lap time minus the driver's median in that race: removes car pace and circuit length
TARGET = "lap_time_delta_s"

log = logging.getLogger(__name__)


def add_target(laps: pd.DataFrame) -> pd.DataFrame:
    """Add TARGET, lap_frac and stint_id to one race's green-flag laps."""
    out = laps.copy()
    out[TARGET] = out["lap_time_s"] - out.groupby("driver")["lap_time_s"].transform("median")
    out["lap_frac"] = out["lap"] / out["total_laps"]
    out["stint_id"] = (
        out["session_key"].astype(str) + "-" + out["driver"] + "-" + out["stint"].astype(str)
    )
    return out


def build_pace_dataset(years: list[int]) -> pd.DataFrame:
    """Green-flag laps from every completed race in `years`, with TARGET and race keys added.

    Slow on first use (OpenF1 rate limit, about 15 s per race); cached afterwards.
    """
    frames = []
    now = pd.Timestamp.now(tz="UTC")
    for year in years:
        races = openf1.sessions(year)
        if races.empty:
            continue
        races = races[(races["session_name"] == "Race") & (races["date_start"] < now)]
        for rnd, race in enumerate(races.to_dict("records"), start=1):
            try:
                session = openf1.load_session(int(race["session_key"]))
                laps = green_flag_laps(race_laps(session))
            except (ValueError, KeyError) as e:  # no lap data, wet race with no slick laps
                log.warning("skip %s %s: %s", year, race["circuit_short_name"], e)
                continue
            if laps.empty:
                continue
            laps = laps.assign(
                year=year,
                round=rnd,
                circuit=race["circuit_short_name"],
                session_key=int(race["session_key"]),
            )
            frames.append(add_target(laps))
    if not frames:
        raise ValueError(f"No race laps found for {years}")
    df = pd.concat(frames, ignore_index=True)
    log.info("pace dataset: %d laps from %d races", len(df), df["session_key"].nunique())
    return df


def time_series_splits(
    df: pd.DataFrame, n_splits: int = 4
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Expanding-window splits by race [M13]: every test race is after every train race.

    Yields positional (train_idx, test_idx); a race is never split across the two.
    """
    race = (df["year"] * 100 + df["round"]).to_numpy()
    chunks = np.array_split(np.unique(race), n_splits + 1)
    for i in range(1, n_splits + 1):
        train = np.concatenate(chunks[:i])
        yield np.flatnonzero(np.isin(race, train)), np.flatnonzero(np.isin(race, chunks[i]))
