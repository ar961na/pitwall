"""race_laps / green_flag_laps / safety-car detection on a hand-built fake session."""

import pandas as pd

from pitwall.data.laps import green_flag_laps, race_laps
from pitwall.data.openf1 import Session


def fake_session() -> Session:
    s = object.__new__(Session)  # skip the network-loading __init__
    s.key = 1
    s.info = {"year": 2025, "circuit_short_name": "Test", "session_name": "Race", "circuit_key": 1}
    s.drivers = pd.DataFrame(
        {"driver_number": [1, 4], "name_acronym": ["VER", "NOR"], "team_name": ["RB", "McL"]}
    )
    s.laps_raw = pd.DataFrame(
        [
            {
                "driver_number": d,
                "lap_number": n,
                "lap_duration": None if n == 1 else 90.0 + 0.05 * n,
                "is_pit_out_lap": n == 6,
                "date_start": pd.Timestamp("2025-01-01", tz="UTC"),
            }
            for d in (1, 4)
            for n in range(1, 11)
        ]
    )
    s.stints = pd.DataFrame(
        [
            {
                "driver_number": d,
                "stint_number": 1,
                "lap_start": 1,
                "lap_end": 5,
                "compound": "MEDIUM",
                "tyre_age_at_start": 0,
            }
            for d in (1, 4)
        ]
        + [
            {
                "driver_number": d,
                "stint_number": 2,
                "lap_start": 6,
                "lap_end": 10,
                "compound": "HARD",
                "tyre_age_at_start": 3,
            }
            for d in (1, 4)
        ]
    )
    s.pits = pd.DataFrame({"driver_number": [1, 4], "lap_number": [5, 5]})
    s.race_control = pd.DataFrame(
        [
            {
                "lap_number": 7,
                "category": "SafetyCar",
                "flag": None,
                "message": "SAFETY CAR DEPLOYED",
            },
            {
                "lap_number": 8,
                "category": "SafetyCar",
                "flag": None,
                "message": "SAFETY CAR IN THIS LAP",
            },
        ]
    )
    s.results = pd.DataFrame(
        {"driver_number": [1, 4], "position": [1, 2], "number_of_laps": [10, 10]}
    )
    return s


def test_neutralised_laps_include_restart_lap():
    assert fake_session().neutralised_laps() == {7: "4", 8: "4", 9: "4"}


def test_race_laps_columns_and_tyre_life():
    df = race_laps(fake_session())
    ver = df[df.driver == "VER"].set_index("lap")
    assert ver.loc[3, "compound"] == "MEDIUM" and ver.loc[3, "tyre_life"] == 3
    assert ver.loc[6, "compound"] == "HARD" and ver.loc[6, "tyre_life"] == 4  # used set, age 3 + 1
    assert ver.loc[5, "pit_in"] and ver.loc[6, "pit_out"]
    assert ver.loc[8, "track_status"] == "4"
    assert ver.loc[2, "laps_remaining"] == 8


def test_green_flag_filter():
    g = green_flag_laps(race_laps(fake_session()))
    assert set(g["lap"]) == {2, 3, 4, 10}  # no lap 1, no in/out laps 5/6, no SC laps 7-9
