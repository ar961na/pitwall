from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from pitwall.api.routes.degradation import fit_race
from pitwall.data.openf1 import circuit_info
from pitwall.models.pace_gbm import PaceModelMissingError, load_model, tyre_terms
from pitwall.models.tyre_deg import cliff_ages
from pitwall.strategy.calibrate import params_from_degradation
from pitwall.strategy.params import RaceParams
from pitwall.strategy.policies import simulate_reactive
from pitwall.strategy.simulator import (
    RaceScenarios,
    Stint,
    Strategy,
    clean_lap_times,
    optimize,
    simulate,
)

router = APIRouter(tags=["strategy"])


class OptimizeRequest(BaseModel):
    params: RaceParams = Field(default_factory=RaceParams)
    max_stops: int = Field(2, ge=1, le=3)
    min_stint: int = Field(8, ge=3)
    n_sims: int = Field(2000, ge=100, le=20000)
    seed: int = 0
    reactive: bool = Field(False, description="Rank with early stops under a safety car")


@router.get("/strategy/defaults")
def defaults() -> RaceParams:
    return RaceParams()


@router.get("/sessions/{session_key}/strategy/calibrate")
def calibrate(session_key: int, driver: str | None = None) -> RaceParams:
    """Simulator parameters fitted to a real race (tyre model + circuit pit loss).

    Compounds whose race fit is missing or implausible take their degradation from the
    multi-race pace model when one is trained, else from the illustrative defaults.
    """
    session, laps, model = fit_race(session_key)
    if driver and driver not in model.driver_offset:
        raise HTTPException(404, f"No green-flag laps for {driver}")
    overrides = {}
    info = circuit_info(session.info["circuit_key"], session.info["year"])
    if info and info.get("pitLoss"):
        normal, sc = float(info["pitLoss"]["normal"]), float(info["pitLoss"]["sc"])
        overrides = {"pit_loss_s": normal, "sc_pit_loss_factor": round(sc / normal, 3)}
    try:
        terms = tyre_terms(
            load_model(), str(session.info["circuit_short_name"]), session.total_laps
        )
        pace_deg = {c: deg for c, (_, deg) in terms.items()}
    except PaceModelMissingError:
        pace_deg = None
    return params_from_degradation(
        model,
        total_laps=session.total_laps,
        driver=driver,
        cliffs=cliff_ages(laps, model),
        pace_deg=pace_deg,
        **overrides,
    )


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
        simulator=simulate_reactive if req.reactive else None,
    )
    # Same seed as optimize(), so these are the scenarios the ranking was computed on.
    scenarios = RaceScenarios.sample(req.params, req.n_sims, req.seed)
    for i, row in enumerate(rows):
        strat = Strategy(tuple(Stint(s["compound"], s["laps"]) for s in row["stints"]))
        fixed = simulate(strat, req.params, scenarios)
        reactive = simulate_reactive(strat, req.params, scenarios)
        row["reactive_gain_s"] = round(fixed.mean - reactive.mean, 3)
        if i < 3:  # lap-time traces for the chart
            row["clean_lap_times_s"] = clean_lap_times(strat, req.params).round(3).tolist()
    return {"params": req.params, "reactive": req.reactive, "results": rows}
