import numpy as np
import pandas as pd

from pitwall.telemetry.compare import compare_laps, minisector_dominance, resample_on_distance
from tests.conftest import corner_profile, make_lap_telemetry


def test_resample_is_regular_and_ends_at_finish():
    tel = make_lap_telemetry(lambda d: 250.0)
    r = resample_on_distance(tel, step_m=10.0)
    assert r["distance"].iloc[0] == 0.0
    assert np.isclose(r["distance"].iloc[-1], tel["distance"].max())
    assert np.allclose(np.diff(r["distance"])[:-1], 10.0)
    assert np.isclose(r["time"].iloc[-1], tel["time_s"].iloc[-1])


def test_resample_drops_backwards_distance_jitter():
    tel = make_lap_telemetry(lambda d: 250.0)
    jitter = tel.iloc[[5]].assign(distance=tel["distance"].iloc[3])  # goes backwards
    tel = pd.concat([tel.iloc[:6], jitter, tel.iloc[6:]]).reset_index(drop=True)
    r = resample_on_distance(tel)
    assert np.all(np.diff(r["time"]) >= 0)


def test_delta_matches_lap_time_difference():
    a = make_lap_telemetry(corner_profile([(1000, 100, 120), (3000, 150, 100)]))
    b = make_lap_telemetry(corner_profile([(1000, 95, 130), (3000, 150, 100)]))
    cmp = compare_laps(a, b)
    lap_diff = b["time_s"].iloc[-1] - a["time_s"].iloc[-1]
    assert lap_diff > 0  # B is slower through corner 1
    assert np.isclose(cmp["delta"].iloc[-1], lap_diff, atol=1e-6)
    # B loses time around corner 1 only
    before = cmp.loc[cmp["distance"] < 800, "delta"]
    assert np.allclose(before, 0, atol=1e-6)


def test_minisectors_sum_to_total_delta():
    a = make_lap_telemetry(corner_profile([(1000, 100, 120)]))
    b = make_lap_telemetry(corner_profile([(1000, 110, 140)]))
    cmp = compare_laps(a, b)
    ms = minisector_dominance(cmp, n_sectors=20)
    assert np.isclose(ms["gain_b_s"].sum(), -cmp["delta"].iloc[-1], atol=1e-6)
