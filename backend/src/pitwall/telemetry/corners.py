"""Corner-by-corner analysis.

Corner positions come from the MultiViewer circuit API [D3] (hand-made, "sufficient for
visualization" per FastF1's docs); they're mapped to lap distance by nearest XY point [M3],
like FastF1's CircuitInfo.add_marker_distance. See docs/REFERENCES.md.
"""

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
    """Per-corner comparison of two drivers on a `compare_laps` frame.

    The corner zone is apex ± `window_m`; the braking point is searched before the apex only.
    Returns one row per corner: corner, apex_m, min_speed_a/_b (km/h), brake_point_a/_b
    (m, NaN if the driver never brakes on entry) and time_gain_b_s (> 0: B faster).
    """
    d = cmp["distance"].to_numpy(float)
    rows = []
    for number, apex in zip(corners["number"].tolist(), corners["distance"].tolist(), strict=True):
        lo, hi = max(apex - window_m, d[0]), min(apex + window_m, d[-1])
        zone = (d >= lo) & (d <= hi)
        entry = (d >= lo) & (d <= apex)
        row: dict[str, float] = {"corner": int(number), "apex_m": apex}
        spent = {}
        for s in "ab":
            row[f"min_speed_{s}"] = float(cmp.loc[zone, f"speed_{s}"].min())
            braking = d[entry & cmp[f"brake_{s}"].to_numpy(bool)]
            row[f"brake_point_{s}"] = float(braking[0]) if braking.size else float("nan")
            # interpolate at the exact zone edges so the result doesn't depend on grid alignment
            t_lo, t_hi = np.interp([lo, hi], d, cmp[f"time_{s}"].to_numpy(float))
            spent[s] = t_hi - t_lo
        row["time_gain_b_s"] = float(spent["a"] - spent["b"])
        rows.append(row)
    out = pd.DataFrame(
        rows,
        columns=[
            "corner",
            "apex_m",
            "min_speed_a",
            "min_speed_b",
            "brake_point_a",
            "brake_point_b",
            "time_gain_b_s",
        ],
    )
    return out.astype({"corner": int})
