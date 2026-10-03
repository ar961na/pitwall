from __future__ import annotations

import pandas as pd
from fastapi import APIRouter, HTTPException

from pitwall.api.utils import get_session
from pitwall.data import openf1

router = APIRouter(tags=["events"])


@router.get("/events/{year}")
def events(year: int) -> list[dict]:
    """Race weekends of a season with their sessions (session_key is what other endpoints take)."""
    try:
        mtgs, sess = openf1.meetings(year), openf1.sessions(year)
    except Exception as e:
        raise HTTPException(502, f"Could not load {year} calendar: {e}") from e
    if mtgs.empty:
        return []
    now = pd.Timestamp.now(tz="UTC")
    out = []
    for rnd, m in enumerate(mtgs.itertuples(), start=1):
        s = sess[sess["meeting_key"] == m.meeting_key]
        out.append(
            {
                "round": rnd,
                "meeting_key": int(m.meeting_key),
                "name": m.meeting_name,
                "circuit": m.circuit_short_name,
                "country": m.country_name,
                "date": m.date_start.date().isoformat(),
                "sessions": [
                    {
                        "session_key": int(x.session_key),
                        "name": x.session_name,
                        "date": x.date_start.isoformat(),
                        "completed": bool(x.date_start + pd.Timedelta(hours=3) < now),
                    }
                    for x in s.itertuples()
                ],
            }
        )
    return out


@router.get("/sessions/{session_key}/drivers")
def drivers(session_key: int) -> list[dict]:
    session = get_session(session_key)
    pos = {}
    if not session.results.empty and "position" in session.results:
        pos = dict(zip(session.results["driver_number"], session.results["position"], strict=True))
    out = []
    for d in session.drivers.itertuples():
        p = pos.get(d.driver_number)
        out.append(
            {
                "number": int(d.driver_number),
                "code": d.name_acronym,
                "name": d.full_name,
                "team": d.team_name,
                "color": f"#{d.team_colour or '888888'}",
                "position": None if p is None or pd.isna(p) else int(p),
            }
        )
    return sorted(out, key=lambda d: d["position"] or 99)
