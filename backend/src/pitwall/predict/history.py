"""Historical results + qualifying from Jolpica (the maintained Ergast successor), 1950 → today.

Source [D2]: Jolpica F1 API, https://github.com/jolpica/jolpica-f1, Ergast-compatible endpoints
`/ergast/f1/{year}/results.json` and `/ergast/f1/{year}/qualifying.json`.
Data licence CC BY-NC-SA 4.0, non-commercial use, attribution required (TERMS.md in that repo).
"""

import datetime as dt

import pandas as pd

from pitwall.data.http import CachedClient

# Jolpica limits without a token: 4 req/s burst, 500 req/h (their docs/rate_limits.md).
# In practice 0.5 s spacing still drew 429s (2026-11), so requests are 1 s apart.
client = CachedClient("https://api.jolpi.ca/ergast/f1", "jolpica", min_interval_s=1.0)


def _paged(path: str, table: str, year: int) -> list[dict]:
    ttl = 6 * 3600 if year >= dt.date.today().year else None  # current season keeps changing
    races: dict[str, dict] = {}
    offset, total = 0, 1
    while offset < total:
        data = client.get(f"{path}?limit=100&offset={offset}", ttl_s=ttl)["MRData"]
        total, offset = int(data["total"]), offset + int(data["limit"])
        for race in data["RaceTable"]["Races"]:
            # a race can be split across pages: merge its rows
            races.setdefault(race["round"], {**race, table: []})[table].extend(race.get(table, []))
    return list(races.values())


def _time_s(t: str | None) -> float | None:
    if not t:
        return None
    m, _, s = t.rpartition(":")
    return (int(m) * 60 if m else 0) + float(s)


def season_results(year: int) -> pd.DataFrame:
    rows = []
    for race in _paged(f"{year}/results.json", "Results", year):
        for r in race["Results"]:
            rows.append(
                {
                    "year": year,
                    "round": int(race["round"]),
                    "race_name": race["raceName"],
                    "circuit_id": race["Circuit"]["circuitId"],
                    "date": race["date"],
                    "driver_id": r["Driver"]["driverId"],
                    "driver_code": r["Driver"].get("code"),
                    "constructor_id": r["Constructor"]["constructorId"],
                    "grid": int(r["grid"]),  # 0 = pit-lane start
                    "position": int(r["position"]),
                    "position_text": r["positionText"],  # "R" retired, "D" disqualified, ...
                    "status": r["status"],
                    "points": float(r["points"]),
                    "laps": int(r["laps"]),
                }
            )
    return pd.DataFrame(rows)


def season_qualifying(year: int) -> pd.DataFrame:
    rows = []
    for race in _paged(f"{year}/qualifying.json", "QualifyingResults", year):
        for q in race["QualifyingResults"]:
            rows.append(
                {
                    "year": year,
                    "round": int(race["round"]),
                    "race_name": race["raceName"],
                    "circuit_id": race["Circuit"]["circuitId"],
                    "date": race["date"],
                    "driver_id": q["Driver"]["driverId"],
                    "driver_code": q["Driver"].get("code"),
                    "constructor_id": q["Constructor"]["constructorId"],
                    "quali_pos": int(q["position"]),
                    "q1_s": _time_s(q.get("Q1")),
                    "q2_s": _time_s(q.get("Q2")),
                    "q3_s": _time_s(q.get("Q3")),
                }
            )
    return pd.DataFrame(rows)


QUALI_COLUMNS = ["quali_pos", "q1_s", "q2_s", "q3_s"]


def season_schedule(year: int) -> pd.DataFrame:
    """Calendar of a season: round, race_name, circuit_id, date."""
    ttl = 6 * 3600 if year >= dt.date.today().year else None
    races = client.get(f"{year}.json?limit=100", ttl_s=ttl)["MRData"]["RaceTable"]["Races"]
    return pd.DataFrame(
        [
            {
                "year": year,
                "round": int(r["round"]),
                "race_name": r["raceName"],
                "circuit_id": r["Circuit"]["circuitId"],
                "date": r["date"],
            }
            for r in races
        ]
    )


def fetch_results(years: list[int]) -> pd.DataFrame:
    """Results joined with qualifying, one row per (year, round, driver), sorted in time."""
    res = pd.concat([season_results(y) for y in years], ignore_index=True)
    quali = pd.concat([season_qualifying(y) for y in years], ignore_index=True)
    df = res
    if not quali.empty:
        keys = ["year", "round", "driver_id"]
        df = res.merge(quali[[*keys, *QUALI_COLUMNS]], on=keys, how="left")
    for col in QUALI_COLUMNS:
        if col not in df:
            df[col] = float("nan")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["date", "position"]).reset_index(drop=True)
