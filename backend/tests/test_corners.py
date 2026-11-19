import numpy as np
import pandas as pd
import pytest

from pitwall.telemetry.compare import compare_laps
from pitwall.telemetry.corners import corner_analysis
from tests.conftest import corner_profile, make_lap_telemetry

CORNERS = pd.DataFrame({"number": [1, 2], "distance": [1000.0, 3000.0]})


@pytest.fixture
def table():
    # Corner 1: B brakes 30 m later (brake zone 100 vs 130 m) and carries 10 km/h more.
    # Corner 2: identical.
    a = make_lap_telemetry(corner_profile([(1000, 100, 130), (3000, 150, 100)]), hz=10)
    b = make_lap_telemetry(corner_profile([(1000, 110, 100), (3000, 150, 100)]), hz=10)
    return corner_analysis(compare_laps(a, b, step_m=2.0), CORNERS)


def test_shape_and_columns(table):
    assert list(table["corner"]) == [1, 2]
    expected = {
        "corner",
        "apex_m",
        "min_speed_a",
        "min_speed_b",
        "brake_point_a",
        "brake_point_b",
        "time_gain_b_s",
    }
    assert expected <= set(table.columns)


def test_min_speed(table):
    c1 = table.set_index("corner").loc[1]
    assert c1["min_speed_a"] == pytest.approx(100, abs=3)
    assert c1["min_speed_b"] == pytest.approx(110, abs=3)


def test_brake_points(table):
    c1 = table.set_index("corner").loc[1]
    assert c1["brake_point_a"] == pytest.approx(870, abs=15)
    assert c1["brake_point_b"] == pytest.approx(900, abs=15)


def test_time_gain_sign_and_identical_corner(table):
    t = table.set_index("corner")
    assert t.loc[1, "time_gain_b_s"] > 0.05
    assert abs(t.loc[2, "time_gain_b_s"]) < 0.01


def test_no_braking_gives_nan():
    flat = make_lap_telemetry(lambda d: 250.0)
    out = corner_analysis(compare_laps(flat, flat), CORNERS)
    assert np.isnan(out["brake_point_a"]).all()


def test_detect_corners_finds_braking_zones():
    from pitwall.telemetry.corners import detect_corners

    a = make_lap_telemetry(corner_profile([(1000, 100, 130), (3000, 150, 100)]), hz=10)
    b = make_lap_telemetry(corner_profile([(1000, 110, 100), (3000, 150, 100)]), hz=10)
    found = detect_corners(compare_laps(a, b, step_m=2.0))
    assert list(found["number"]) == [1, 2]
    assert (found["source"] == "detected").all()
    assert np.allclose(found["distance"], [1000, 3000], atol=20)


def test_detect_corners_ignores_flat_out_laps():
    from pitwall.telemetry.corners import detect_corners

    flat = make_lap_telemetry(lambda d: 300.0 - 5 * np.sin(d / 300))  # small wiggles, no braking
    assert detect_corners(compare_laps(flat, flat)).empty
