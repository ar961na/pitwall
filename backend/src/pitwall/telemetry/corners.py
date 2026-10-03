"""Corner-by-corner analysis — TASK 1 (docs/tasks/01-corner-analysis.md).

Corner positions come from the MultiViewer circuit API [D3] (hand-made, "sufficient for
visualization" per FastF1's docs); they're mapped to lap distance by nearest XY point [M3],
like FastF1's CircuitInfo.add_marker_distance. See docs/REFERENCES.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def locate_corners(circuit: dict | None, cmp: pd.DataFrame) -> pd.DataFrame:
    """Corner apexes (from MultiViewer circuit info) projected onto the lap's distance axis.

    Each corner's XY is matched to the nearest point of driver A's racing line in `cmp`.
    Returns columns: number, letter, distance, x, y  (empty if no circuit info / no XY).
    """
    cols = ["number", "letter", "distance", "x", "y"]
    if not circuit or not circuit.get("corners") or "x_a" not in cmp:
        return pd.DataFrame(columns=cols)
    line = np.column_stack([cmp["x_a"], cmp["y_a"]])
    rows = []
    for c in circuit["corners"]:
        xy = np.array([c["trackPosition"]["x"], c["trackPosition"]["y"]])
        i = int(np.argmin(((line - xy) ** 2).sum(axis=1)))
        rows.append([c["number"], c.get("letter") or "", float(cmp["distance"].iloc[i]), *xy])
    return pd.DataFrame(rows, columns=cols).sort_values("distance").reset_index(drop=True)


def corner_analysis(
    cmp: pd.DataFrame, corners: pd.DataFrame, window_m: float = 250.0
) -> pd.DataFrame:
    """Per-corner comparison of two drivers.

    Args:
        cmp: output of `compare_laps` (distance, speed_a/b, throttle_a/b, brake_a/b, time_a/b ...).
        corners: output of `locate_corners` — at least `number` and `distance` (apex, m).
        window_m: how far before the apex to look for the braking point.

    Returns:
        One row per corner with columns:
            corner            int    corner number
            apex_m            float  apex distance
            min_speed_a/_b    float  minimum speed in the corner zone (km/h)
            brake_point_a/_b  float  where braking starts before the apex (m), NaN if no braking
            time_gain_b_s     float  time B gains vs A through the corner zone (> 0: B faster)
    """
    raise NotImplementedError("TASK 1 — see docs/tasks/01-corner-analysis.md")
