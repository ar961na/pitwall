# Task 1: Corner-by-corner analysis

**File:** `backend/src/pitwall/telemetry/corners.py` → `corner_analysis()`
**Check:** `pytest -m task tests/tasks/test_task1_corners.py`
**Shows up in:** the "Corner by corner" table on the Telemetry page.

## Goal

Given two distance-aligned laps (`compare_laps` output) and the corner apex positions, produce
one row per corner: minimum speed for each driver, braking point for each driver, and the time B
gains through the corner. This is the bread-and-butter output of a performance engineer: "Lando
loses 0.08 s in T4 because he brakes 12 m earlier and carries 4 km/h less to the apex".

## Before you start

Read `telemetry/compare.py` and `tests/conftest.py` (`make_lap_telemetry`, `corner_profile`).
In a notebook, plot `speed_a`, `brake_a` and `delta` for a real lap:

```python
from pitwall.data import openf1
from pitwall.telemetry.compare import compare_laps
from pitwall.telemetry.corners import locate_corners

s = openf1.load_session(openf1.find_session(2026, "monza", "Qualifying"))
cmp = compare_laps(s.lap_telemetry("VER"), s.lap_telemetry("NOR"))
corners = locate_corners(openf1.circuit_info(s.info["circuit_key"], 2026), cmp)
```

## Concept refresher

- **Why work in distance rather than time?** At a given time the two cars are in different places.
  At a given distance they're at the same piece of track.
- **Time gained over a zone** = (time A took to cover [d0, d1]) − (time B took). `time_a` and
  `time_b` are cumulative, so you only need them at the two zone edges. `np.interp` gives the
  value at an exact distance, so you don't depend on grid alignment.
- **The braking point** is the first distance before the apex where the brake channel turns on. The
  real feed is ~4 Hz (≈20 m between samples at 300 km/h), so your answer can only be as good as
  the data. That makes a good interview talking point.

<details><summary>Hint 1: structure</summary>

Loop over `corners.itertuples()`. For each apex, build two boolean masks on `cmp["distance"]`:
an *entry* window `[apex - window_m, apex]` for the braking point, and a *zone*
`[apex - window_m, apex + window_m]` for min speed and time gain.
</details>

<details><summary>Hint 2: braking point</summary>

`cmp.loc[entry & cmp["brake_a"].astype(bool), "distance"]`: take the first value, or `np.nan`
if it's empty. Don't take the *last* braking sample. Why not?
</details>

<details><summary>Hint 3: time gain without off-by-one errors</summary>

```python
lo, hi = max(apex - window_m, 0), min(apex + window_m, d[-1])
ta = np.interp([lo, hi], d, cmp["time_a"])
```
gain_b = (ta[1] - ta[0]) - (tb[1] - tb[0]). Check: summed over non-overlapping zones, it should
match `-delta` over those zones.
</details>

## Stretch

1. **No circuit info?** MultiViewer doesn't know brand-new tracks (e.g. Kuala Lumpur 2026), so
   `locate_corners` returns nothing. Write `detect_corners(cmp)` that finds corners as local
   speed minima with `scipy.signal.find_peaks(-speed, prominence=…, distance=…)`, and fall back
   to it in the API route.
2. **Lap-time attribution:** across all drivers in a qualifying session, regress each driver's gap
   to pole on per-corner features (min speed, braking point, exit speed at apex + 100 m). Which
   corners "explain" the gap? That's the "model that explains lap-time delta" from your original
   project idea.

## Interview questions to prepare

- Why resample on distance, and what goes wrong at the start/finish line?
- How would sampling rate (4 Hz vs a team's 1 kHz) change your braking-point uncertainty?
- Delta at the line is exact (0.650 s), but minisector deltas aren't independent. Why?

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [D1] OpenF1 `car_data` (~3.7 Hz) and `location`; [D3] MultiViewer corners
- [M1] interpolation onto a distance grid, [M2] distance integration (FastF1 approach), [M3] corner → distance, [M4] `scipy.signal.find_peaks`
