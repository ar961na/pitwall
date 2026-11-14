"""Finishing-order predictor: a LambdaMART ranker plus Plackett-Luce probabilities.

Two variants are trained: "post_quali" uses grid and qualifying pace, "pre_quali" only form and
history, so a forecast exists before Saturday as well.

Method (docs/REFERENCES.md): LightGBM lambdarank [M9, M21] ranks the drivers of one race;
scores become win and podium probabilities by sampling finishing orders from a Plackett-Luce
model [M22] with the Gumbel trick [M27]; one temperature, fitted on out-of-fold scores, keeps
the win probabilities honest [M16]; evaluation uses race-ordered expanding splits [M13].
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy import optimize, stats
from scipy.special import logsumexp

from pitwall.models.pace_gbm import time_series_splits
from pitwall.predict.features import build_features

log = logging.getLogger(__name__)

FORM_FEATURES = [
    "driver_form_pos",
    "team_form_pos",
    "driver_track_best",
    "driver_points_before",
    "team_points_before",
]
GRID_FEATURES = ["grid_eff", "quali_pos", "quali_gap_pct"]
VARIANTS = {"post_quali": GRID_FEATURES + FORM_FEATURES, "pre_quali": FORM_FEATURES}

# Chosen among seven configurations by race-ordered CV on 2014-2026 (226 test races): small
# trees and a top-10 label with exponential gain were the only setup that matched grid order on
# picking the winner (55%) while beating it on overall rank correlation (0.659 vs 0.622).
TOP_N = 10
LGBM_PARAMS: dict[str, Any] = {
    "objective": "lambdarank",
    "n_estimators": 60,
    "learning_rate": 0.05,
    "num_leaves": 4,
    "min_child_samples": 60,
    "subsample": 0.8,
    "subsample_freq": 1,
    "colsample_bytree": 0.8,
    "label_gain": [2**i - 1 for i in range(TOP_N + 2)],
    "random_state": 0,
    "verbose": -1,
}
N_SAMPLES = 20000  # simulated finishing orders per race; p_win standard error below 0.004
SEED = 0


def _race_id(df: pd.DataFrame) -> pd.Series:
    return df["year"] * 100 + df["round"]


def _fit(df: pd.DataFrame, features: list[str]) -> lgb.LGBMRanker:
    """`df` must be sorted so each race's rows are contiguous."""
    sizes = df.groupby(_race_id(df), sort=False).size().to_numpy()
    # winner gets TOP_N, tenth place 1, everyone else 0: the front of the field matters most
    relevance = np.maximum(0, TOP_N + 1 - df["position"]).astype(int)
    model = lgb.LGBMRanker(**LGBM_PARAMS)
    model.fit(df[features], relevance, group=sizes)
    return model


def _scores(model: lgb.LGBMRanker, x: pd.DataFrame) -> np.ndarray:
    return np.asarray(model.predict(x), dtype=float)


def sample_orders(
    scores: np.ndarray, temperature: float, n_samples: int = N_SAMPLES, seed: int = SEED
) -> np.ndarray:
    """Finishing positions (n_samples, n_drivers), 1 = winner, from a Plackett-Luce model.

    Adding Gumbel noise to score / temperature and sorting is an exact Plackett-Luce draw [M27].
    """
    rng = np.random.default_rng(seed)
    noisy = scores[None, :] / temperature + rng.gumbel(size=(n_samples, len(scores)))
    order = np.argsort(-noisy, axis=1)
    positions = np.empty_like(order)
    np.put_along_axis(positions, order, np.arange(1, len(scores) + 1)[None, :], axis=1)
    return positions


def _winner_nll(log_t: float, races: list[tuple[np.ndarray, int]]) -> float:
    t = np.exp(log_t)
    total = 0.0
    for scores, winner in races:
        z = scores / t
        total -= z[winner] - logsumexp(z)
    return total / len(races)


def fit_temperature(races: list[tuple[np.ndarray, int]]) -> float:
    """Temperature minimising the winner's negative log-likelihood under softmax(score / T)."""
    res = optimize.minimize_scalar(_winner_nll, bounds=(-4, 4), args=(races,), method="bounded")
    return float(np.exp(res.x))


@dataclass
class RacePredictor:
    features: list[str]
    model: lgb.LGBMRanker
    temperature: float
    metrics: dict = field(default_factory=dict)

    def predict(self, race: pd.DataFrame) -> pd.DataFrame:
        """Per-driver forecast for one race's feature rows."""
        scores = _scores(self.model, race[self.features])
        positions = sample_orders(scores, self.temperature)
        return pd.DataFrame(
            {
                "predicted_position": stats.rankdata(-scores, method="ordinal").astype(int),
                "expected_position": positions.mean(axis=0),
                "p_win": (positions == 1).mean(axis=0),
                "p_podium": (positions <= 3).mean(axis=0),
            },
            index=race.index,
        )


def _race_metrics(scores: np.ndarray, actual: np.ndarray) -> dict[str, float]:
    predicted = stats.rankdata(-scores, method="ordinal")
    rho = stats.spearmanr(predicted, actual).statistic
    return {
        "spearman": float(rho),
        "winner_hit": float(predicted[np.argmin(actual)] == 1),
        "podium_overlap": float(
            len(set(np.flatnonzero(predicted <= 3)) & set(np.flatnonzero(actual <= 3))) / 3
        ),
    }


def evaluate(df: pd.DataFrame, features: list[str], n_splits: int = 5) -> tuple[dict, float]:
    """Race-ordered CV. Returns mean metrics (model and grid-order baseline) and the temperature.

    The temperature and the Brier score are computed on the same out-of-fold scores, so the
    reported Brier score is slightly optimistic.
    """
    per_race: list[dict[str, float]] = []
    baseline: list[dict[str, float]] = []
    oof: list[tuple[np.ndarray, int]] = []
    for train_idx, test_idx in time_series_splits(df, n_splits):
        model = _fit(df.iloc[train_idx], features)
        test = df.iloc[test_idx]
        for _, race in test.groupby(_race_id(test), sort=False):
            scores = _scores(model, race[features])
            actual = race["position"].to_numpy()
            per_race.append(_race_metrics(scores, actual))
            oof.append((scores, int(np.argmin(actual))))
            if "grid_eff" in race:
                baseline.append(_race_metrics(-race["grid_eff"].to_numpy(float), actual))

    temperature = fit_temperature(oof)
    brier = []
    for scores, winner in oof:
        p = np.exp(scores / temperature - logsumexp(scores / temperature))
        brier.append(float(np.mean((p - (np.arange(len(p)) == winner)) ** 2)))

    metrics = {k: float(np.mean([m[k] for m in per_race])) for k in per_race[0]}
    metrics["brier_win"] = float(np.mean(brier))
    metrics["n_test_races"] = len(per_race)
    for k in ("spearman", "winner_hit", "podium_overlap"):
        metrics[f"grid_baseline_{k}"] = float(np.mean([m[k] for m in baseline]))
    return metrics, temperature


def training_frame(results: pd.DataFrame) -> pd.DataFrame:
    """Features for every finished race, sorted by race, rows of one race contiguous."""
    df = build_features(results)
    df = df[df["position"].notna()].sort_values(["year", "round", "position"])
    return df.reset_index(drop=True)


def train(results: pd.DataFrame, n_splits: int = 5) -> dict[str, RacePredictor]:
    """Evaluate with CV, then refit each variant on all finished races."""
    df = training_frame(results)
    out = {}
    for name, features in VARIANTS.items():
        metrics, temperature = evaluate(df, features, n_splits)
        out[name] = RacePredictor(features, _fit(df, features), temperature, metrics)
        log.info(
            "%s: spearman %.3f (grid order %.3f), winner %.0f%% (%.0f%%), %d test races",
            name,
            metrics["spearman"],
            metrics["grid_baseline_spearman"],
            100 * metrics["winner_hit"],
            100 * metrics["grid_baseline_winner_hit"],
            metrics["n_test_races"],
        )
    return out
