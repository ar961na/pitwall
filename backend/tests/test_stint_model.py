"""Stint forecaster on synthetic stints with an accelerating (non-linear) wear curve."""

import numpy as np
import pandas as pd
import pytest

torch = pytest.importorskip("torch")  # optional `dl` extra; CI's test install skips these

from pitwall.dl import stint_model  # noqa: E402
from pitwall.dl.stint_dataset import SEQ_FEATURES  # noqa: E402
from pitwall.models.pace_gbm import TARGET  # noqa: E402


def fake_laps(n_races: int = 12, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for race in range(n_races):
        for d in range(6):
            lap = 1
            for stint, compound in enumerate(["MEDIUM", "HARD"], start=1):
                for age in range(1, 21):
                    wear = 0.002 * age**2.2  # accelerating, so persistence and lines both lag
                    rows.append(
                        {
                            "year": 2024 + race // 6,
                            "round": race % 6 + 1,
                            "session_key": race,
                            "driver": f"D{d}",
                            "stint": stint,
                            "lap": lap,
                            "compound": compound,
                            "tyre_life": float(age),
                            "laps_remaining": 40 - lap,
                            TARGET: wear + rng.normal(0, 0.05),
                        }
                    )
                    lap += 1
    return pd.DataFrame(rows)


def test_stint_frame_splits_on_missing_laps():
    laps = fake_laps(n_races=1)
    one = laps[(laps["driver"] == "D0") & (laps["stint"] == 1)]
    holed = one[one["lap"] != 10]  # e.g. a safety-car lap removed by the green-flag filter
    framed = stint_model.stint_frame(holed)
    assert framed["stint_id"].nunique() == 2
    assert {"compound_soft", "compound_medium", "compound_hard"} <= set(framed.columns)


def test_baselines_on_known_series():
    x = np.zeros((1, 8, len(SEQ_FEATURES)), np.float32)
    x[0, :, SEQ_FEATURES.index(TARGET)] = np.arange(8)  # +1 s per lap
    assert np.allclose(stint_model.persistence(x), [[7, 7, 7]])
    assert np.allclose(stint_model.linear_extrapolation(x), [[8, 9, 10]])


def test_race_split_keeps_time_order():
    laps = fake_laps()
    train, val = stint_model.race_split(laps)
    key = lambda d: d["year"] * 100 + d["round"]  # noqa: E731
    assert key(train).max() < key(val).min()


def test_training_beats_persistence(monkeypatch):
    model = stint_model.train(fake_laps(), epochs=25, device=torch.device("cpu"))
    m = model.metrics
    assert m["n_train_windows"] > 0 and m["n_val_windows"] > 0
    assert m["mae_gru_s"] < m["mae_persistence_s"]
    x = np.zeros((2, stint_model.CONTEXT, len(SEQ_FEATURES)), np.float32)
    assert model.predict(x).shape == (2, stint_model.HORIZON)
