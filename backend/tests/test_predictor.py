"""Race predictor on synthetic seasons where the true pace order is known."""

import numpy as np
import pandas as pd
import pytest

from pitwall.predict import history, service
from pitwall.predict.model import VARIANTS, fit_temperature, sample_orders, train

N_DRIVERS, N_ROUNDS = 10, 12


def season(year: int, rng: np.random.Generator, rounds: int = N_ROUNDS) -> pd.DataFrame:
    """Driver i has skill i (0 is best); qualifying and race are skill plus noise."""
    rows = []
    for rnd in range(1, rounds + 1):
        quali = np.argsort(np.argsort(np.arange(N_DRIVERS) + rng.normal(0, 1.0, N_DRIVERS))) + 1
        finish = np.argsort(np.argsort(np.arange(N_DRIVERS) + rng.normal(0, 1.5, N_DRIVERS))) + 1
        for i in range(N_DRIVERS):
            rows.append(
                {
                    "year": year,
                    "round": rnd,
                    "race_name": f"GP {rnd}",
                    "circuit_id": f"c{rnd}",
                    "date": pd.Timestamp(year, 3, 1) + pd.Timedelta(weeks=rnd),
                    "driver_id": f"d{i}",
                    "driver_code": f"D{i:02d}",
                    "constructor_id": f"t{i // 2}",
                    "grid": int(quali[i]),
                    "position": int(finish[i]),
                    "points": float(max(0, 11 - finish[i])),
                    "quali_pos": int(quali[i]),
                    "q1_s": 80.0 + 0.1 * quali[i],
                    "q2_s": np.nan,
                    "q3_s": np.nan,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="module")
def results() -> pd.DataFrame:
    rng = np.random.default_rng(1)
    return pd.concat([season(y, rng) for y in range(2018, 2024)], ignore_index=True)


@pytest.fixture(scope="module")
def predictors(results):
    return train(results, n_splits=3)


def test_sample_orders_are_permutations_and_favour_high_scores():
    pos = sample_orders(np.array([2.0, 0.0, -2.0]), temperature=1.0, n_samples=4000)
    assert (np.sort(pos, axis=1) == [1, 2, 3]).all()
    p_win = (pos == 1).mean(axis=0)
    assert p_win[0] > p_win[1] > p_win[2]
    # Plackett-Luce: P(win) is the softmax of the scores
    expected = np.exp([2.0, 0.0, -2.0]) / np.exp([2.0, 0.0, -2.0]).sum()
    assert np.allclose(p_win, expected, atol=0.03)


def test_temperature_grows_when_scores_are_overconfident():
    rng = np.random.default_rng(0)
    races = []
    for _ in range(300):
        scores = rng.normal(0, 1, 8)
        p = np.exp(scores) / np.exp(scores).sum()
        races.append((scores * 5, int(rng.choice(8, p=p))))  # scores inflated five-fold
    assert fit_temperature(races) == pytest.approx(5.0, rel=0.25)


def test_both_variants_train_and_learn_the_order(predictors):
    assert set(predictors) == set(VARIANTS)
    for p in predictors.values():
        assert p.metrics["spearman"] > 0.5
        assert p.temperature > 0
        assert p.metrics["n_test_races"] > 0


def test_predict_gives_proper_probabilities(predictors, results):
    from pitwall.predict.model import training_frame

    frame = training_frame(results)
    race = frame[(frame["year"] == 2023) & (frame["round"] == N_ROUNDS)]
    out = predictors["post_quali"].predict(race)
    assert sorted(out["predicted_position"]) == list(range(1, N_DRIVERS + 1))
    assert out["p_win"].sum() == pytest.approx(1.0)
    assert out["p_podium"].sum() == pytest.approx(3.0)
    assert out["p_win"].between(0, 1).all()


@pytest.fixture
def fake_history(monkeypatch, results):
    """2024 season: rounds 1-2 finished, round 3 qualified, round 4 not yet."""
    rng = np.random.default_rng(7)
    new = season(2024, rng, rounds=4)
    full = pd.concat([results, new[new["round"] <= 2]], ignore_index=True)

    def season_results(year):
        return full[full["year"] == year]

    def season_qualifying(year):
        src = pd.concat([results, new[new["round"] <= 3]])
        # like Jolpica's qualifying endpoint: no race result columns
        return src[src["year"] == year].drop(columns=["grid", "position", "points"])

    def season_schedule(year):
        src = pd.concat([results, new])
        cols = ["year", "round", "race_name", "circuit_id", "date"]
        return src[src["year"] == year][cols].drop_duplicates("round")

    def fetch_results(years):
        return (
            full[full["year"].isin(years)].sort_values(["date", "position"]).reset_index(drop=True)
        )

    for name, fn in [
        ("season_results", season_results),
        ("season_qualifying", season_qualifying),
        ("season_schedule", season_schedule),
        ("fetch_results", fetch_results),
    ]:
        monkeypatch.setattr(history, name, fn)
    return full


@pytest.fixture
def bundle(predictors):
    return {
        "predictors": predictors,
        "years": [2018, 2023],
        "n_races": 72,
        "last_race": [2023, N_ROUNDS],
        "trained_at": "2024-01-01T00:00:00+00:00",
    }


def test_rounds_report_their_state(fake_history):
    states = {r["round"]: r["state"] for r in service.rounds(2024)}
    assert states == {1: "finished", 2: "finished", 3: "qualified", 4: "upcoming"}


def test_finished_round_is_scored_and_flagged(fake_history, bundle):
    out = service.predict_round(2024, 2, bundle)
    assert out["state"] == "finished" and out["variant"] == "post_quali"
    assert out["in_training_data"] is False  # trained up to 2023 only
    assert -1 <= out["score"]["spearman"] <= 1
    assert all(d["actual_position"] is not None for d in out["drivers"])
    assert service.predict_round(2023, 5, bundle)["in_training_data"] is True


def test_qualified_round_uses_grid_from_qualifying(fake_history, bundle):
    out = service.predict_round(2024, 3, bundle)
    assert out["state"] == "qualified" and out["variant"] == "post_quali"
    assert out["score"] is None
    assert all(d["grid"] is not None and d["actual_position"] is None for d in out["drivers"])


def test_upcoming_round_uses_form_only(fake_history, bundle):
    out = service.predict_round(2024, 4, bundle)
    assert out["state"] == "upcoming" and out["variant"] == "pre_quali"
    assert len(out["drivers"]) == N_DRIVERS
    assert all(d["grid"] is None for d in out["drivers"])
    assert sum(d["p_win"] for d in out["drivers"]) == pytest.approx(1.0, abs=1e-3)


def test_future_results_do_not_change_a_forecast(fake_history, bundle, monkeypatch):
    before = service.predict_round(2024, 1, bundle)["drivers"]
    tampered = fake_history.copy()
    later = (tampered["year"] == 2024) & (tampered["round"] == 2)
    tampered.loc[later, "position"] = tampered.loc[later, "position"].to_numpy()[::-1]
    monkeypatch.setattr(
        history,
        "fetch_results",
        lambda years: (
            tampered[tampered["year"].isin(years)]
            .sort_values(["date", "position"])
            .reset_index(drop=True)
        ),
    )
    after = service.predict_round(2024, 1, bundle)["drivers"]
    assert [(d["driver_id"], d["p_win"]) for d in before] == [
        (d["driver_id"], d["p_win"]) for d in after
    ]


def test_unknown_round_is_an_error(fake_history, bundle):
    with pytest.raises(ValueError, match="no round"):
        service.predict_round(2024, 9, bundle)
