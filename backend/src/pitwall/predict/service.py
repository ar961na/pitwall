"""Train, store and apply the race predictor for a given round.

A round is forecast in one of three states: "finished" (results exist, so the forecast can be
scored), "qualified" (qualifying exists: post_quali model) or "upcoming" (neither: pre_quali
model, entry list taken from the latest finished race).
"""

import datetime as dt
import logging
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from scipy import stats

from pitwall.config import settings
from pitwall.predict import history
from pitwall.predict.features import build_features
from pitwall.predict.model import RacePredictor, train

log = logging.getLogger(__name__)

MODEL_PATH = settings.models_dir / "race_predictor.joblib"
# Assumption: start with the hybrid-engine era; older cars and points systems differ too much.
FIRST_YEAR = 2014


class ModelMissingError(RuntimeError):
    pass


def train_and_save(last_year: int, path: Path | None = None) -> dict:
    path = path or MODEL_PATH
    years = list(range(FIRST_YEAR, last_year + 1))
    results = history.fetch_results(years)
    bundle = {
        "predictors": train(results),
        "years": [FIRST_YEAR, last_year],
        "n_races": int(results.groupby(["year", "round"]).ngroups),
        "trained_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, path)
    log.info("saved %s (%d races)", path, bundle["n_races"])
    return bundle


@lru_cache(maxsize=2)
def _load(path: Path, mtime: float) -> dict:
    return joblib.load(path)


def load_bundle(path: Path | None = None) -> dict:
    path = path or MODEL_PATH
    if not path.exists():
        raise ModelMissingError(
            "No trained race predictor. Train one with `make train-predictor` "
            "(python backend/scripts/train_race_predictor.py)."
        )
    return _load(path, path.stat().st_mtime)


def rounds(year: int) -> list[dict]:
    """Calendar of `year` with the forecast state of every round."""
    schedule = history.season_schedule(year)
    done = set(history.season_results(year).get("round", []))
    qualified = set(history.season_qualifying(year).get("round", []))
    out = []
    for r in schedule.to_dict("records"):
        state = (
            "finished"
            if r["round"] in done
            else "qualified"
            if r["round"] in qualified
            else "upcoming"
        )
        out.append({"round": r["round"], "name": r["race_name"], "date": r["date"], "state": state})
    return out


def _entry_rows(year: int, rnd: int, past: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Rows for a round without results: from its qualifying, else from the latest race's entries."""
    race = history.season_schedule(year)
    race = race[race["round"] == rnd]
    if race.empty:
        raise ValueError(f"{year} has no round {rnd}")
    info = race.iloc[0]
    quali = history.season_qualifying(year)
    quali = quali[quali["round"] == rnd] if not quali.empty else quali
    if not quali.empty:
        rows = quali.assign(grid=quali["quali_pos"])
        state = "qualified"
    else:
        if past.empty:
            raise ValueError("No earlier race to take the entry list from")
        last = past[past["date"] == past["date"].max()]
        rows = last[["driver_id", "driver_code", "constructor_id"]].assign(year=year)
        rows["round"] = rnd
        state = "upcoming"
    rows = rows.assign(
        race_name=info["race_name"], circuit_id=info["circuit_id"], date=pd.Timestamp(info["date"])
    )
    return rows, state


def predict_round(year: int, rnd: int, bundle: dict | None = None) -> dict:
    bundle = bundle or load_bundle()
    results = history.fetch_results(list(range(bundle["years"][0], year + 1)))
    this = (results["year"] == year) & (results["round"] == rnd)
    if this.any():
        state = "finished"
        table = results[(results["date"] <= results.loc[this, "date"].iloc[0])]
    else:
        rows, state = _entry_rows(year, rnd, results)
        table = pd.concat(
            [results[results["date"] < rows["date"].iloc[0]], rows], ignore_index=True
        )

    features = build_features(table)
    race = features[(features["year"] == year) & (features["round"] == rnd)].reset_index(drop=True)
    variant = "pre_quali" if state == "upcoming" else "post_quali"
    predictor: RacePredictor = bundle["predictors"][variant]
    out = race.join(predictor.predict(race)).sort_values("predicted_position")

    score = None
    if state == "finished":
        rho = stats.spearmanr(out["predicted_position"], out["position"]).statistic
        winner = out.iloc[int(np.argmin(out["position"].to_numpy()))]
        score = {
            "spearman": round(float(rho), 3),
            "winner_predicted": bool(winner["predicted_position"] == 1),
            "winner_p_win": round(float(winner["p_win"]), 3),
        }

    def opt_int(v) -> int | None:
        return None if v is None or (isinstance(v, float) and np.isnan(v)) else int(v)

    return {
        "year": year,
        "round": rnd,
        "race_name": str(out["race_name"].iloc[0]),
        "state": state,
        "variant": variant,
        "score": score,
        "model": {
            "trained_at": bundle["trained_at"],
            "years": bundle["years"],
            "n_races": bundle["n_races"],
            "cv": {k: round(v, 3) for k, v in predictor.metrics.items()},
        },
        "drivers": [
            {
                "driver_id": r["driver_id"],
                "code": r["driver_code"]
                if isinstance(r["driver_code"], str)
                else r["driver_id"][:3].upper(),
                "constructor_id": r["constructor_id"],
                "grid": opt_int(r.get("grid")),
                "predicted_position": int(r["predicted_position"]),
                "expected_position": round(float(r["expected_position"]), 2),
                "p_win": round(float(r["p_win"]), 4),
                "p_podium": round(float(r["p_podium"]), 4),
                "actual_position": opt_int(r.get("position")),
            }
            for r in out.to_dict("records")
        ],
    }
