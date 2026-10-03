"""Live-data checks. Run with:  pytest -m network   (slow the first time: OpenF1 rate limits)."""

import pytest

from pitwall.data import openf1
from pitwall.data.laps import green_flag_laps, race_laps
from pitwall.predict.history import fetch_results

pytestmark = pytest.mark.network


def test_openf1_race_loads():
    key = openf1.find_session(2025, "zandvoort")
    s = openf1.load_session(key)
    assert s.total_laps == 72
    assert 23 in s.neutralised_laps()  # first safety car
    g = green_flag_laps(race_laps(s))
    assert len(g) > 500


def test_jolpica_results():
    df = fetch_results([2024])
    assert df["round"].nunique() == 24
    assert {"grid", "position", "quali_pos", "constructor_id"} <= set(df.columns)
