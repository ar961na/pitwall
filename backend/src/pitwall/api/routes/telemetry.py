from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from pitwall.api.utils import columns, get_session, records
from pitwall.data.openf1 import circuit_info
from pitwall.telemetry.compare import compare_laps, minisector_dominance
from pitwall.telemetry.corners import corner_analysis, locate_corners

router = APIRouter(tags=["telemetry"])


@router.get("/sessions/{session_key}/compare")
def compare(
    session_key: int,
    a: str = Query(..., description="Driver code, e.g. VER"),
    b: str = Query(..., description="Driver code, e.g. NOR"),
    step_m: float = Query(5.0, ge=1.0, le=50.0),
) -> dict:
    """Fastest lap of A vs fastest lap of B, aligned on distance."""
    session = get_session(session_key)
    try:
        lap_a, lap_b = session.fastest_lap(a), session.fastest_lap(b)
        cmp = compare_laps(session.lap_telemetry(a), session.lap_telemetry(b), step_m=step_m)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e

    corners = locate_corners(circuit_info(session.info["circuit_key"], session.info["year"]), cmp)
    try:
        corner_table, corner_status = records(corner_analysis(cmp, corners)), "ok"
    except NotImplementedError as e:
        corner_table, corner_status = None, str(e)

    def lap_info(code, lap) -> dict:
        return {
            "driver": code.upper(),
            "lap_number": int(lap["lap_number"]),
            "lap_time_s": float(lap["lap_duration"]),
        }

    return {
        "session": session.name,
        "a": lap_info(a, lap_a),
        "b": lap_info(b, lap_b),
        "channels": columns(cmp),
        "minisectors": records(minisector_dominance(cmp)),
        "corners": records(corners),
        "corner_analysis": corner_table,
        "corner_analysis_status": corner_status,
    }
