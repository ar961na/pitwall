from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pitwall.api.routes.degradation import fit_race
from pitwall.data.openf1 import circuit_info
from pitwall.strategy.calibrate import params_from_degradation
from pitwall.strategy.params import RaceParams
from pitwall.strategy.simulator import Stint, Strategy, clean_lap_times, optimize

router = APIRouter(tags=["strategy"])


class OptimizeRequest(BaseModel):
    params: RaceParams = Field(default_factory=RaceParams)
    max_stops: int = Field(2, ge=1, le=3)
    min_stint: int = Field(8, ge=3)
    n_sims: int = Field(2000, ge=100, le=20000)
    seed: int = 0


@router.get("/strategy/defaults")
def defaults() -> RaceParams:
    return RaceParams()


@router.get("/sessions/{session_key}/strategy/calibrate")
def calibrate(session_key: int, driver: str | None = None) -> RaceParams:
    """Simulator parameters fitted to a real race (tyre model + circuit pit loss)."""
    session, laps, model = fit_race(session_key)
    if driver and driver not in model.driver_offset:
        raise HTTPException(404, f"No green-flag laps for {driver}")
    overrides = {}
    info = circuit_info(session.info["circuit_key"], session.info["year"])
    if info and info.get("pitLoss"):
        normal, sc = float(info["pitLoss"]["normal"]), float(info["pitLoss"]["sc"])
        overrides = {"pit_loss_s": normal, "sc_pit_loss_factor": round(sc / normal, 3)}
    return params_from_degradation(model, total_laps=session.total_laps, driver=driver, **overrides)


@router.post("/strategy/optimize")
def run_optimize(req: OptimizeRequest) -> dict:
    if req.max_stops == 3 and req.params.total_laps > 60:
        raise HTTPException(422, "3-stop search on long races is too slow for the API; use 2")
    rows = optimize(
        req.params,
        max_stops=req.max_stops,
        min_stint=req.min_stint,
        n_sims=req.n_sims,
        seed=req.seed,
    )
    # Lap-time traces for the top 3 so the UI can plot them.
    for row in rows[:3]:
        strat = Strategy(tuple(Stint(s["compound"], s["laps"]) for s in row["stints"]))
        row["clean_lap_times_s"] = clean_lap_times(strat, req.params).round(3).tolist()
    return {"params": req.params, "results": rows}
