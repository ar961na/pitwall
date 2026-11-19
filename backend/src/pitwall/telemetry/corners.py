"""Corner-by-corner analysis.

Corner positions come from the MultiViewer circuit API [D3] (hand-made, "sufficient for
visualization" per FastF1's docs); they're mapped to lap distance by nearest XY point [M3],
like FastF1's CircuitInfo.add_marker_distance. Brand-new circuits have no published corners
(MultiViewer answers 404), so `detect_corners` falls back to braking zones found as minima of
the speed trace [M4]. See docs/REFERENCES.md.
"""

import numpy as np
import pandas as pd
from scipy.signal import find_peaks

COLUMNS = ["number", "letter", "distance", "x", "y", "source"]
# Minimum speed drop (km/h) for a speed minimum to count as a braking zone, and the minimum
# distance between two zones. Chosen on Monza 2026, Zandvoort 2025 and Interlagos 2026: every
# zone found lay within 100 m of a published corner. Flat-out corners are not found, by design.
MIN_DROP_KMH = 10.0
MIN_GAP_M = 150.0


def locate_corners(circuit: dict | None, cmp: pd.DataFrame) -> pd.DataFrame:
    """Corner apexes (from MultiViewer circuit info) projected onto the lap's distance axis.

    Each corner's XY is matched to the nearest point of driver A's racing line in `cmp`.
    Returns COLUMNS with source "published" (empty if no circuit info / no XY).
    """
    if not circuit or not circuit.get("corners") or "x_a" not in cmp:
        return pd.DataFrame(columns=COLUMNS)
    line = np.column_stack([cmp["x_a"], cmp["y_a"]])
    rows = []
    for c in circuit["corners"]:
        xy = np.array([c["trackPosition"]["x"], c["trackPosition"]["y"]])
        i = int(np.argmin(((line - xy) ** 2).sum(axis=1)))
        rows.append(
            [c["number"], c.get("letter") or "", float(cmp["distance"].iloc[i]), *xy, "published"]
        )
    return pd.DataFrame(rows, columns=COLUMNS).sort_values("distance").reset_index(drop=True)


def detect_corners(cmp: pd.DataFrame) -> pd.DataFrame:
    """Braking zones as minima of both drivers' mean speed, numbered in lap order.

    Returns COLUMNS with source "detected". Numbers are zone numbers, not official corner numbers.
    """
    speed = ((cmp["speed_a"] + cmp["speed_b"]) / 2).to_numpy(float)
    d = cmp["distance"].to_numpy(float)
    step = float(np.median(np.diff(d))) if len(d) > 1 else 1.0
    peaks, _ = find_peaks(-speed, prominence=MIN_DROP_KMH, distance=max(1, round(MIN_GAP_M / step)))
    x = cmp["x_a"].to_numpy(float) if "x_a" in cmp else np.full(len(d), np.nan)
    y = cmp["y_a"].to_numpy(float) if "y_a" in cmp else np.full(len(d), np.nan)
    rows = [[n, "", d[i], x[i], y[i], "detected"] for n, i in enumerate(peaks, start=1)]
    return pd.DataFrame(rows, columns=COLUMNS)


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
