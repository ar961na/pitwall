"""Distance-aligned lap comparison.

Telemetry is sampled in *time* (~4 Hz car data from OpenF1), but two laps
can only be compared meaningfully in *space*: "at 1200 m into the lap, A was doing 280 km/h
and B 284 km/h". So we resample every channel onto a common distance grid, and the time
delta between the drivers falls out of the interpolated time-at-distance.

Distance is integrated from speed, so two laps of the same track come out a few metres
different in length; `compare_laps` rescales both onto a common lap length first.

Methods (docs/REFERENCES.md): [M1] linear interpolation onto a distance grid (np.interp),
[M2] distance from integrated speed, as in FastF1's Telemetry.integrate_distance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

_CONTINUOUS = ("speed", "throttle", "rpm", "x", "y")


def resample_on_distance(
    tel: pd.DataFrame, step_m: float = 5.0, length_m: float | None = None
) -> pd.DataFrame:
    """Interpolate a telemetry frame (needs distance + time_s) onto a regular distance grid."""
    d = tel["distance"].to_numpy(float)
    t = tel["time_s"].to_numpy(float)
    # np.interp needs strictly increasing x; drop samples where distance stalls or jitters back.
    keep = d > np.maximum.accumulate(np.concatenate([[-np.inf], d[:-1]]))
    d, t = d[keep], t[keep]

    end = length_m if length_m is not None else d[-1]
    grid = np.append(np.arange(0.0, end, step_m), end)  # always include the finish line
    out = {"distance": grid, "time": np.interp(grid, d, t)}
    for ch in _CONTINUOUS:
        if ch in tel:
            out[ch] = np.interp(grid, d, tel[ch].to_numpy(float)[keep])
    if "gear" in tel:
        out["gear"] = np.rint(np.interp(grid, d, tel["gear"].to_numpy(float)[keep])).astype(int)
    if "brake" in tel:
        out["brake"] = np.interp(grid, d, tel["brake"].to_numpy(float)[keep]) > 0.5
    return pd.DataFrame(out)


def compare_laps(tel_a: pd.DataFrame, tel_b: pd.DataFrame, step_m: float = 5.0) -> pd.DataFrame:
    """Side-by-side channels on one grid. `delta` = time_b - time_a (positive: B is behind)."""
    len_a, len_b = tel_a["distance"].max(), tel_b["distance"].max()
    length = (len_a + len_b) / 2
    a = resample_on_distance(
        tel_a.assign(distance=tel_a["distance"] * length / len_a), step_m, length
    )
    b = resample_on_distance(
        tel_b.assign(distance=tel_b["distance"] * length / len_b), step_m, length
    )
    out = (
        a.drop(columns=["distance"])
        .add_suffix("_a")
        .join(b.drop(columns=["distance"]).add_suffix("_b"))
    )
    out.insert(0, "distance", a["distance"])
    out["delta"] = out["time_b"] - out["time_a"]
    return out


def minisector_dominance(cmp: pd.DataFrame, n_sectors: int = 25) -> pd.DataFrame:
    """Split the lap into equal-length minisectors and say who was quicker through each."""
    edges = np.linspace(0, cmp["distance"].iloc[-1], n_sectors + 1)
    spent_a = np.diff(np.interp(edges, cmp["distance"], cmp["time_a"]))
    spent_b = np.diff(np.interp(edges, cmp["distance"], cmp["time_b"]))
    return pd.DataFrame(
        {
            "start_m": edges[:-1],
            "end_m": edges[1:],
            "gain_b_s": spent_a - spent_b,  # > 0: B faster here; sums to -(final delta)
        }
    )
