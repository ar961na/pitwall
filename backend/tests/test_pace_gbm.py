"""Pace model on synthetic races with a known, non-linear tyre effect."""

import numpy as np
import pandas as pd
import pytest

from pitwall.models import pace_gbm
from pitwall.models.pace_gbm import FEATURES, TARGET, PaceModel, add_target, evaluate

DEG = {"SOFT": 0.09, "MEDIUM": 0.05, "HARD": 0.03}
CLIFF = {"SOFT": 14, "MEDIUM": 22, "HARD": 32}


def fake_laps(n_races: int = 10, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    frames = []
    for race in range(n_races):
        rows = []
        for d in range(8):
            lap = 1
            for stint, compound in enumerate(rng.permutation(list(DEG))[:2], start=1):
                for age in range(1, 26):
                    wear = DEG[compound] * age + 0.05 * max(age - CLIFF[compound], 0) ** 2
                    rows.append(
                        {
                            "driver": f"D{d}",
                            "lap": lap,
                            "stint": stint,
                            "compound": compound,
                            "tyre_life": float(age),
                            "fresh_tyre": True,
                            "total_laps": 50,
                            "laps_remaining": 50 - lap,
                            # noise grows with tyre age, so the interval must widen too
                            "lap_time_s": 90
                            + 0.3 * d
                            + wear
                            - 0.04 * lap
                            + rng.normal(0, 0.1 + 0.01 * age),
                        }
                    )
                    lap += 1
        laps = pd.DataFrame(rows).assign(
            year=2024 + race // 5, round=race % 5 + 1, circuit=f"c{race % 4}", session_key=race
        )
        frames.append(add_target(laps))
    return pd.concat(frames, ignore_index=True)


@pytest.fixture(autouse=True)
def fewer_trees(monkeypatch):
    # enough for the synthetic effect, and several times faster than the real setting
    monkeypatch.setitem(pace_gbm.LGBM_PARAMS, "n_estimators", 80)


@pytest.fixture(scope="module")
def laps() -> pd.DataFrame:
    return fake_laps()


def test_add_target_centres_each_driver(laps):
    assert {TARGET, "lap_frac", "stint_id", *FEATURES} <= set(laps.columns)
    medians = laps.groupby(["session_key", "driver"])[TARGET].median()
    assert np.allclose(medians, 0, atol=1e-9)


def test_cv_beats_baselines_and_intervals_cover(laps):
    m = evaluate(laps, n_splits=3)
    assert m["mae_gbm_s"] < m["mae_linear_s"] < m["mae_zero_s"]  # the cliff is not linear
    assert 0.65 <= m["coverage_80_conformal"] <= 0.95
    assert m["coverage_80_conformal"] >= m["coverage_80_raw"]
    assert m["n_test_laps"] > 0


def test_predict_orders_quantiles_and_learns_the_cliff(laps):
    model = PaceModel.fit(laps)
    probe = laps[(laps["compound"] == "SOFT") & (laps["driver"] == "D0")].head(25)
    pred = model.predict(probe)
    assert list(pred.columns) == ["lo", "median", "hi"]
    assert (pred["lo"] <= pred["median"]).all() and (pred["median"] <= pred["hi"]).all()
    early = pred["median"].iloc[8] - pred["median"].iloc[3]  # ages 4 -> 9
    late = pred["median"].iloc[23] - pred["median"].iloc[18]  # ages 19 -> 24, past the cliff
    assert late > 2 * early


def test_unseen_circuit_still_predicts(laps):
    model = PaceModel.fit(laps)
    probe = laps.head(20).assign(circuit="brand_new_track")
    assert model.predict(probe).notna().all().all()


def test_conformal_margin_restores_coverage():
    rng = np.random.default_rng(0)
    y = rng.normal(0, 2.0, 5000)
    lo, hi = np.full_like(y, -1.0), np.full_like(y, 1.0)  # far too narrow for sd 2
    margin = pace_gbm.conformal_margin(lo, hi, y, coverage=0.8)
    covered = ((y >= lo - margin) & (y <= hi + margin)).mean()
    assert covered == pytest.approx(0.8, abs=0.02)
    assert pace_gbm.conformal_margin(lo * 10, hi * 10, y, coverage=0.8) < 0  # too wide: shrinks
