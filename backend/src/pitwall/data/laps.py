"""Turn an OpenF1 session into tidy, model-ready lap tables.

Source: OpenF1 [D1] `laps` (lap/sector times, pit-out flag), `stints` (compound, tyre age at
stint start), `pit` (in-laps) and `race_control` (neutralised laps). See docs/REFERENCES.md.
"""

import logging

import numpy as np
import pandas as pd

SLICK_COMPOUNDS = ("SOFT", "MEDIUM", "HARD")
# Assumption: laps slower than 107% of a driver's median are traffic, mistakes or unflagged
# incidents. The number borrows F1's 107% qualifying rule; it is not fitted to data.
OUTLIER_FACTOR = 1.07

log = logging.getLogger(__name__)


def race_laps(session) -> pd.DataFrame:
    """One row per lap: driver, team, lap, stint, compound, tyre_life, lap_time_s, sectors,
    track_status ("1" green, "4" SC, "6" VSC, "5" red), pit_in / pit_out, laps_remaining."""
    laps = session.laps_raw.rename(
        columns={
            "lap_number": "lap",
            "lap_duration": "lap_time_s",
            "duration_sector_1": "s1_s",
            "duration_sector_2": "s2_s",
            "duration_sector_3": "s3_s",
            "is_pit_out_lap": "pit_out",
        }
    )
    cols = ["driver_number", "lap", "lap_time_s", "s1_s", "s2_s", "s3_s", "pit_out", "date_start"]
    df = laps[[c for c in cols if c in laps]].copy()
    df["pit_out"] = df["pit_out"].eq(True)

    # Expand stints (lap_start..lap_end) to one row per lap.
    st = session.stints.dropna(subset=["lap_start", "lap_end"])
    per_lap = [
        {
            "driver_number": s.driver_number,
            "lap": lap,
            "stint": int(s.stint_number),
            "compound": str(s.compound).upper(),
            "tyre_life": float(s.tyre_age_at_start + (lap - s.lap_start) + 1),
            "fresh_tyre": s.tyre_age_at_start == 0,
        }
        for s in st.itertuples()
        for lap in range(int(s.lap_start), int(s.lap_end) + 1)
    ]
    if per_lap:
        df = df.merge(pd.DataFrame(per_lap), on=["driver_number", "lap"], how="left")
    else:
        df[["stint", "compound", "tyre_life", "fresh_tyre"]] = np.nan

    pit_laps = set()
    if not session.pits.empty:
        pit_laps = set(zip(session.pits["driver_number"], session.pits["lap_number"], strict=True))
    df["pit_in"] = [
        (d, lap) in pit_laps for d, lap in zip(df["driver_number"], df["lap"], strict=True)
    ]

    neutral = session.neutralised_laps()
    df["track_status"] = df["lap"].map(neutral).fillna("1")

    drivers = session.drivers.set_index("driver_number")
    df["driver"] = (
        df["driver_number"].map(drivers["name_acronym"]).fillna(df["driver_number"].astype(str))
    )
    df["team"] = df["driver_number"].map(drivers["team_name"])
    df["total_laps"] = session.total_laps
    df["laps_remaining"] = df["total_laps"] - df["lap"]
    df["compound"] = df["compound"].fillna("UNKNOWN")
    log.info("%s: %d laps from %d drivers", session.name, len(df), df["driver"].nunique())
    return df.sort_values(["driver", "lap"]).reset_index(drop=True)


def green_flag_laps(df: pd.DataFrame, max_rel_to_median: float = OUTLIER_FACTOR) -> pd.DataFrame:
    """Representative racing laps: green flag, no pit in/out, slicks, not lap 1, no outliers."""
    mask = (
        (df["track_status"] == "1")
        & ~df["pit_in"]
        & ~df["pit_out"]
        & df["compound"].isin(SLICK_COMPOUNDS)
        & (df["lap"] > 1)
        & df["lap_time_s"].notna()
        & df["tyre_life"].notna()
    )
    out = df[mask].copy()
    median = out.groupby("driver")["lap_time_s"].transform("median")
    out = out[out["lap_time_s"] <= median * max_rel_to_median].reset_index(drop=True)
    log.info("green-flag filter kept %d of %d laps", len(out), len(df))
    return out
