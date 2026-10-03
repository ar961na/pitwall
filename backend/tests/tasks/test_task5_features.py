"""TASK 5 acceptance tests. Run:  pytest -m task tests/tasks/test_task5_features.py"""

import numpy as np
import pandas as pd
import pytest

from pitwall.predict.features import build_features

pytestmark = pytest.mark.task


@pytest.fixture
def results():
    rng = np.random.default_rng(0)
    rows = []
    drivers = {f"d{i}": f"team{i // 2}" for i in range(6)}
    for year in (2023, 2024):
        for rnd in range(1, 9):
            order = rng.permutation(list(drivers))
            for pos, d in enumerate(order, start=1):
                rows.append(
                    {
                        "year": year,
                        "round": rnd,
                        "date": pd.Timestamp(year, 3, 1) + pd.Timedelta(weeks=rnd),
                        "circuit_id": f"c{rnd}",
                        "driver_id": d,
                        "constructor_id": drivers[d],
                        "grid": int(rng.integers(1, 7)),
                        "position": pos,
                        "quali_pos": int(rng.integers(1, 7)),
                    }
                )
    return pd.DataFrame(rows)


REQUIRED = ["grid", "driver_form_pos", "team_form_pos", "driver_track_best"]


def test_columns_and_row_identity(results):
    f = build_features(results)
    assert set(REQUIRED) <= set(f.columns)
    assert len(f) == len(results)
    assert (
        f[["year", "round", "driver_id"]].to_numpy()
        == results[["year", "round", "driver_id"]].to_numpy()
    ).all()


def test_first_race_has_no_history(results):
    f = build_features(results)
    first = f[(f.year == 2023) & (f["round"] == 1)]
    assert first["driver_form_pos"].isna().all()
    assert first["driver_track_best"].isna().all()


def test_driver_form_is_mean_of_previous_five(results):
    f = build_features(results).set_index(["year", "round", "driver_id"])
    prev = results[
        (results.driver_id == "d0") & (results.year == 2023) & results["round"].between(2, 6)
    ]
    assert f.loc[(2023, 7, "d0"), "driver_form_pos"] == pytest.approx(prev["position"].mean())


def test_track_best_uses_previous_seasons_only(results):
    f = build_features(results).set_index(["year", "round", "driver_id"])
    best = results[(results.driver_id == "d3") & (results.year == 2023) & (results["round"] == 4)][
        "position"
    ].min()
    assert f.loc[(2024, 4, "d3"), "driver_track_best"] == best


def test_no_leakage_from_the_future(results):
    """Changing results of the LAST race must not change any feature of earlier races."""
    before = build_features(results)
    tampered = results.copy()
    last = (tampered.year == 2024) & (tampered["round"] == 8)
    tampered.loc[last, "position"] = tampered.loc[last, "position"].to_numpy()[::-1]
    after = build_features(tampered)
    earlier = ~((before.year == 2024) & (before["round"] == 8))
    pd.testing.assert_frame_equal(before[earlier], after[earlier])
