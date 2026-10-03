"""OpenF1 — laps, stints, pits, race control and ~3.7 Hz car telemetry, 2023 onwards.

Sources (see docs/REFERENCES.md):
    [D1] OpenF1 API, https://openf1.org/docs — endpoints used: sessions, meetings, drivers, laps,
         stints, pit, race_control, session_result, car_data, location.
         Data licence CC BY-NC-SA 4.0 (https://github.com/br-g/openf1) — credit OpenF1,
         non-commercial use only. Unofficial; not associated with Formula 1.
    [D3] MultiViewer circuit API (corners, pit loss), the same endpoint FastF1 uses for
         Session.get_circuit_info(): https://api.multiviewer.app/api/v1/circuits/{key}/{year}
    [D5] F1's live-timing archive (read by FastF1) answered us with HTTP 403 on 2026-10-03,
         so pitwall reads OpenF1 directly.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import quote

import numpy as np
import pandas as pd

from pitwall.data.http import CachedClient

# OpenF1 Community tier: 3 req/s and 30 req/min (https://openf1.org/#sponsorship) — stay under both.
client = CachedClient("https://api.openf1.org/v1", "openf1", min_interval_s=2.1)
multiviewer = CachedClient("https://api.multiviewer.app/api/v1", "multiviewer", min_interval_s=1.0)

DAY = 24 * 3600


def get(endpoint: str, ttl_s: float | None = None, **params) -> pd.DataFrame:
    """`get("laps", session_key=9912)`. Filters like date>= go in as `date__gte="..."`."""
    ops = {"__gte": ">=", "__lte": "<=", "__gt": ">", "__lt": "<"}
    parts = []
    for key, value in params.items():
        op = next((o for suffix, o in ops.items() if key.endswith(suffix)), "=")
        key = next((key.removesuffix(s) for s in ops if key.endswith(s)), key)
        parts.append(f"{key}{op}{quote(str(value), safe=':-.T')}")
    data = client.get(f"{endpoint}?{'&'.join(parts)}", ttl_s=ttl_s, allow_404=True)
    # OpenF1 answers "no rows" with 404 {"detail": "No results found."}
    return pd.DataFrame(data if isinstance(data, list) else [])


def sessions(year: int) -> pd.DataFrame:
    df = get("sessions", ttl_s=DAY, year=year)
    if df.empty:
        return df
    if "is_cancelled" in df:
        df = df[~df["is_cancelled"].fillna(False).astype(bool)]
    df["date_start"] = pd.to_datetime(df["date_start"], utc=True, format="ISO8601")
    return df.sort_values("date_start").reset_index(drop=True)


def meetings(year: int) -> pd.DataFrame:
    df = get("meetings", ttl_s=DAY, year=year)
    if df.empty:
        return df
    df["date_start"] = pd.to_datetime(df["date_start"], utc=True, format="ISO8601")
    df = df[~df["meeting_name"].str.contains("Testing", case=False)]
    if "is_cancelled" in df:  # cancelled weekends don't count as rounds
        df = df[~df["is_cancelled"].fillna(False).astype(bool)]
    return df.sort_values("date_start").reset_index(drop=True)


def find_session(year: int, event: str | int, session_name: str = "Race") -> int:
    """Session key from a round number or a fuzzy name ("monza", "Italy", "Kuala Lumpur")."""
    df = sessions(year)
    df = df[df["session_name"] == session_name]
    if isinstance(event, int) or str(event).isdigit():
        mtgs = meetings(year)["meeting_key"].tolist()
        key = mtgs[int(event) - 1]
        hit = df[df["meeting_key"] == key]
    else:
        needle = str(event).lower()
        text = (
            df["circuit_short_name"] + " " + df["location"] + " " + df["country_name"]
        ).str.lower()
        hit = df[text.str.contains(needle, regex=False)]
    if hit.empty:
        raise ValueError(f"No {session_name} session for {year} / {event!r}")
    return int(hit["session_key"].iloc[0])


def circuit_info(circuit_key: int, year: int) -> dict | None:
    """Corners (with XY), track outline and typical pit loss, from MultiViewer."""
    try:
        return multiviewer.get(f"circuits/{circuit_key}/{year}", allow_404=True)
    except Exception:
        return None


class Session:
    """Everything OpenF1 knows about one session, as DataFrames. Use `load_session(key)`."""

    def __init__(self, session_key: int):
        self.key = session_key
        info = get("sessions", session_key=session_key)
        if info.empty:
            raise ValueError(f"Unknown session_key {session_key}")
        self.info: dict = info.iloc[0].to_dict()
        self.drivers = get("drivers", session_key=session_key).drop_duplicates("driver_number")
        self.laps_raw = get("laps", session_key=session_key)
        self.stints = get("stints", session_key=session_key)
        self.pits = get("pit", session_key=session_key)
        self.race_control = get("race_control", session_key=session_key)
        self.results = get("session_result", session_key=session_key)
        if self.laps_raw.empty:
            raise ValueError(f"No lap data for session {session_key} (yet)")
        self.laps_raw["date_start"] = pd.to_datetime(
            self.laps_raw["date_start"], utc=True, format="ISO8601"
        )

    @property
    def name(self) -> str:
        return f"{self.info['year']} {self.info['circuit_short_name']} {self.info['session_name']}"

    @property
    def total_laps(self) -> int:
        if not self.results.empty and "number_of_laps" in self.results:
            return int(self.results["number_of_laps"].max())
        return int(self.laps_raw["lap_number"].max())

    def driver_code(self, number: int) -> str:
        row = self.drivers[self.drivers["driver_number"] == number]
        return str(row["name_acronym"].iloc[0]) if not row.empty else str(number)

    def driver_number(self, code: str) -> int:
        row = self.drivers[self.drivers["name_acronym"] == code.upper()]
        if row.empty:
            raise ValueError(f"Unknown driver {code!r} in {self.name}")
        return int(row["driver_number"].iloc[0])

    def neutralised_laps(self) -> dict[int, str]:
        """lap_number -> track status code: "4" safety car, "6" VSC, "5" red flag.

        Parsed from OpenF1 `race_control` messages [D1] ("SAFETY CAR DEPLOYED", "... IN THIS LAP",
        "VIRTUAL SAFETY CAR ENDING", red flags). Codes follow F1 live timing's TrackStatus
        convention as documented by FastF1: https://docs.fastf1.dev/api.html
        """
        rc = self.race_control
        status: dict[int, str] = {}
        if rc.empty or "lap_number" not in rc:
            return status
        rc = rc.dropna(subset=["lap_number"])
        open_since: dict[str, int] = {}
        for msg in rc.itertuples():
            text, lap = str(msg.message).upper(), int(msg.lap_number)
            kind = "6" if "VIRTUAL" in text else "4"
            if msg.category == "SafetyCar" and "DEPLOYED" in text:
                open_since[kind] = lap
            elif msg.category == "SafetyCar" and ("IN THIS LAP" in text or "ENDING" in text):
                start = open_since.pop(kind, lap)
                for n in range(start, lap + 1):
                    status[n] = kind
                if kind == "4":
                    status.setdefault(lap + 1, "4")  # restart lap is not representative either
            elif getattr(msg, "flag", None) == "RED":
                status[lap] = "5"
        return status

    def fastest_lap(self, driver: str) -> pd.Series:
        num = self.driver_number(driver)
        laps = self.laps_raw[
            (self.laps_raw["driver_number"] == num) & self.laps_raw["lap_duration"].notna()
        ]
        if laps.empty:
            raise ValueError(f"No timed lap for {driver} in {self.name}")
        return laps.loc[laps["lap_duration"].idxmin()]

    def lap_telemetry(self, driver: str, lap_number: int | None = None) -> pd.DataFrame:
        """Car data + XY position for one lap (fastest if lap_number is None).

        Source: OpenF1 `car_data` and `location` [D1], windowed to the lap's date_start +
        lap_duration. Distance = trapezoidal integral of speed over time [M2] (as FastF1's
        Telemetry.integrate_distance); XY is linearly interpolated onto car-data timestamps [M1].

        Columns: time_s (from lap start), distance (m, integrated from speed), speed, throttle,
        brake, gear, rpm, drs, x, y. Endpoints at t=0 and t=lap_duration are added so the
        time-at-distance curve ends exactly at the official lap time.
        """
        num = self.driver_number(driver)
        if lap_number is None:
            lap = self.fastest_lap(driver)
        else:
            sel = self.laps_raw[
                (self.laps_raw["driver_number"] == num)
                & (self.laps_raw["lap_number"] == lap_number)
            ]
            if sel.empty:
                raise ValueError(f"{driver} has no lap {lap_number}")
            lap = sel.iloc[0]
        start, duration = lap["date_start"], float(lap["lap_duration"])
        end = start + pd.Timedelta(seconds=duration)
        window = {"date__gte": start.isoformat(), "date__lte": end.isoformat()}
        car = get("car_data", session_key=self.key, driver_number=num, **window)
        pos = get("location", session_key=self.key, driver_number=num, **window)
        if car.empty:
            raise ValueError(f"No car telemetry for {driver} lap {int(lap['lap_number'])}")

        car["time_s"] = (pd.to_datetime(car["date"], format="ISO8601") - start).dt.total_seconds()
        car = car.sort_values("time_s").drop_duplicates("time_s")
        # Pin the lap's ends: at t=0 and t=duration, assume the nearest sample's state.
        car = pd.concat(
            [car.iloc[[0]].assign(time_s=0.0), car, car.iloc[[-1]].assign(time_s=duration)]
        ).reset_index(drop=True)

        t = car["time_s"].to_numpy(float)
        v = car["speed"].to_numpy(float) / 3.6
        dist = np.concatenate([[0.0], np.cumsum(np.diff(t) * (v[1:] + v[:-1]) / 2)])

        out = pd.DataFrame(
            {
                "time_s": t,
                "distance": dist,
                "speed": car["speed"].to_numpy(float),
                "throttle": car["throttle"].to_numpy(float),
                "brake": (car["brake"] > 0).to_numpy(float),  # OpenF1 brake is 0/100
                "gear": car["n_gear"].to_numpy(float),
                "rpm": car["rpm"].to_numpy(float),
                "drs": car["drs"].to_numpy(float),
            }
        )
        if not pos.empty:
            pt = (pd.to_datetime(pos["date"], format="ISO8601") - start).dt.total_seconds()
            order = np.argsort(pt.to_numpy())
            out["x"] = np.interp(t, pt.to_numpy()[order], pos["x"].to_numpy(float)[order])
            out["y"] = np.interp(t, pt.to_numpy()[order], pos["y"].to_numpy(float)[order])
        return out


@lru_cache(maxsize=12)
def load_session(session_key: int) -> Session:
    return Session(session_key)
