"""Gradient-boosted pace model across many races.

Predicts a lap's time relative to the driver's median lap in that race from tyre compound and
age, race progress and circuit. Three LightGBM models [M9] trained with the pinball loss [M10]
give the median and an 80% interval. The raw interval was too narrow on later races (64%
coverage on 2023-2026), so it is widened by conformalized quantile regression [M28]: the
latest CALIBRATION_FRACTION of training races measure how far the raw interval misses, and that
margin is added on both sides. Evaluation uses race-ordered expanding splits [M13].
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, Self

import lightgbm as lgb
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


QUANTILES = {"lo": 0.1, "median": 0.5, "hi": 0.9}  # an 80% interval around the median
COVERAGE = QUANTILES["hi"] - QUANTILES["lo"]
CALIBRATION_FRACTION = 0.2  # latest share of training races held out to calibrate the interval
# Untuned defaults; the dataset is tens of thousands of laps, so moderate trees are safe.
LGBM_PARAMS: dict[str, Any] = {
    "objective": "quantile",
    "n_estimators": 300,
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 50,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "random_state": 0,
    "verbose": -1,
}


def _matrix(df: pd.DataFrame, categories: dict[str, list[str]]) -> pd.DataFrame:
    """Feature matrix with fixed category levels, so unseen circuits become missing values."""
    x = df[FEATURES].copy()
    for col in CATEGORICAL:
        x[col] = pd.Categorical(x[col], categories=categories[col])
    x["fresh_tyre"] = x["fresh_tyre"].astype(float)
    return x


def _fit_quantiles(
    df: pd.DataFrame, categories: dict[str, list[str]]
) -> dict[str, lgb.LGBMRegressor]:
    x = _matrix(df, categories)
    return {
        name: lgb.LGBMRegressor(**LGBM_PARAMS, alpha=alpha).fit(x, df[TARGET])
        for name, alpha in QUANTILES.items()
    }


def _raw_predict(models: dict[str, lgb.LGBMRegressor], x: pd.DataFrame) -> np.ndarray:
    raw = np.column_stack([np.asarray(m.predict(x), dtype=float) for m in models.values()])
    # separately trained quantile models can cross; sorting restores lo <= median <= hi
    return np.sort(raw, axis=1)


def conformal_margin(lo: np.ndarray, hi: np.ndarray, y: np.ndarray, coverage: float) -> float:
    """CQR margin [M28]: the finite-sample quantile of max(lo - y, y - hi)."""
    scores = np.maximum(lo - y, y - hi)
    n = len(scores)
    level = min(1.0, np.ceil((n + 1) * coverage) / n)
    return float(np.quantile(scores, level, method="higher"))


@dataclass
class PaceModel:
    models: dict[str, lgb.LGBMRegressor]
    categories: dict[str, list[str]]
    margin: float = 0.0
    metrics: dict = field(default_factory=dict)

    @classmethod
    def fit(cls, df: pd.DataFrame, calibrate: bool = True) -> Self:
        """Fit on all races; with `calibrate`, first measure the CQR margin on the latest races.

        The margin comes from models fitted without the calibration races, then is applied to
        models refitted on everything. That keeps the newest races in the final fit at the cost
        of the exact finite-sample guarantee, which time drift breaks anyway.
        """
        categories = {c: sorted(df[c].astype(str).unique()) for c in CATEGORICAL}
        margin = 0.0
        race = (df["year"] * 100 + df["round"]).to_numpy()
        races = np.unique(race)
        n_cal = int(len(races) * CALIBRATION_FRACTION)
        if calibrate and n_cal >= 1 and len(races) - n_cal >= 1:
            is_cal = np.isin(race, races[-n_cal:])
            early = _fit_quantiles(df[~is_cal], categories)
            cal = df[is_cal]
            pred = _raw_predict(early, _matrix(cal, categories))
            margin = conformal_margin(pred[:, 0], pred[:, 2], cal[TARGET].to_numpy(float), COVERAGE)
        return cls(_fit_quantiles(df, categories), categories, margin)

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """Columns lo, median, hi (seconds relative to the driver's median lap)."""
        pred = _raw_predict(self.models, _matrix(df, self.categories))
        pred[:, 0] -= self.margin
        pred[:, 2] += self.margin
        return pd.DataFrame(pred, columns=list(self.models), index=df.index)


def _linear_baseline(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    """Least squares on compound, tyre age per compound and race progress, pooled over races."""

    def design(d: pd.DataFrame) -> np.ndarray:
        cols = [np.ones(len(d)), d["lap_frac"].to_numpy(float)]
        for c in ("SOFT", "MEDIUM", "HARD"):
            is_c = (d["compound"] == c).to_numpy(float)
            cols += [is_c, is_c * d["tyre_life"].to_numpy(float)]
        return np.column_stack(cols)

    coef, *_ = np.linalg.lstsq(design(train), train[TARGET].to_numpy(float), rcond=None)
    return design(test) @ coef


def evaluate(df: pd.DataFrame, n_splits: int = 4) -> dict[str, float]:
    """Race-ordered CV: MAE against two baselines, and coverage of the raw and calibrated interval."""
    abs_err: dict[str, list[np.ndarray]] = {"gbm": [], "linear": [], "zero": []}
    inside: dict[str, list[np.ndarray]] = {"raw": [], "conformal": []}
    width: dict[str, list[np.ndarray]] = {"raw": [], "conformal": []}
    for train_idx, test_idx in time_series_splits(df, n_splits):
        train, test = df.iloc[train_idx], df.iloc[test_idx]
        model = PaceModel.fit(train)
        pred = model.predict(test)
        y = test[TARGET].to_numpy(float)
        abs_err["gbm"].append(np.abs(pred["median"].to_numpy() - y))
        abs_err["linear"].append(np.abs(_linear_baseline(train, test) - y))
        abs_err["zero"].append(np.abs(y))
        for name, m in (("raw", 0.0), ("conformal", model.margin)):
            lo, hi = (
                pred["lo"].to_numpy() + model.margin - m,
                pred["hi"].to_numpy() - model.margin + m,
            )
            inside[name].append((y >= lo) & (y <= hi))
            width[name].append(hi - lo)
    out = {f"mae_{k}_s": float(np.concatenate(v).mean()) for k, v in abs_err.items()}
    for name in inside:
        out[f"coverage_80_{name}"] = float(np.concatenate(inside[name]).mean())
        out[f"interval_width_{name}_s"] = float(np.concatenate(width[name]).mean())
    out["n_test_laps"] = int(sum(len(v) for v in inside["raw"]))
    return out
