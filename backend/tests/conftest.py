import numpy as np
import pandas as pd
import pytest


def make_lap_telemetry(speed_kmh, length_m: float = 4000.0, hz: float = 4.0) -> pd.DataFrame:
    """Synthetic telemetry in pitwall's format from a speed profile v(distance).

    Integrates the car along the track at `hz`, like a real ~4 Hz car-data feed.
    `speed_kmh` is a function of distance (m) -> km/h. A brake channel is derived from
    deceleration and throttle from acceleration.
    """
    dt = 1.0 / hz
    t, d, rows = 0.0, 0.0, []
    while d < length_m:
        v = float(speed_kmh(d))
        rows.append((t, d, v))
        d += v / 3.6 * dt
        t += dt
    # pin the finish line exactly (fraction of the last step)
    t_prev, d_prev, v_prev = rows[-1]
    rows.append((t_prev + (length_m - d_prev) / (v_prev / 3.6), length_m, v_prev))
    df = pd.DataFrame(rows, columns=["time_s", "distance", "speed"])
    accel = np.gradient(df["speed"].to_numpy(), df["time_s"].to_numpy())
    df["brake"] = (accel < -15).astype(float)
    df["throttle"] = np.where(accel < -15, 0.0, 100.0)
    df["gear"] = np.clip(df["speed"] // 40 + 1, 1, 8)
    df["rpm"] = 10000.0
    df["x"] = np.cos(df["distance"] / length_m * 2 * np.pi) * 1000
    df["y"] = np.sin(df["distance"] / length_m * 2 * np.pi) * 1000
    return df


def corner_profile(corners: list[tuple[float, float, float]], top: float = 300.0):
    """v(d) with V-shaped dips: corners = [(apex_m, min_kmh, brake_len_m), ...].

    Braking starts `brake_len_m` before the apex; acceleration back to `top` takes 2x as long.
    """

    def v(d: float) -> float:
        speed = top
        for apex, vmin, brake_len in corners:
            if apex - brake_len <= d <= apex:
                speed = min(speed, top - (top - vmin) * (d - (apex - brake_len)) / brake_len)
            elif apex < d <= apex + 2 * brake_len:
                speed = min(speed, vmin + (top - vmin) * (d - apex) / (2 * brake_len))
        return speed

    return v


@pytest.fixture
def rng():
    return np.random.default_rng(42)
