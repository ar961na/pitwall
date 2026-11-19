import numpy as np
from fastapi import APIRouter, HTTPException

from pitwall.api.utils import get_session, records
from pitwall.data.laps import green_flag_laps, race_laps
from pitwall.models.pace_gbm import PaceModelMissingError, load_model, tyre_curves
from pitwall.models.tyre_deg import LinearDegradationModel, cliff_ages

router = APIRouter(tags=["degradation"])


def fit_race(session_key: int):
    session = get_session(session_key)
    laps = green_flag_laps(race_laps(session))
    if laps.empty:
        raise HTTPException(422, "No green-flag slick laps in this race (wet race?)")
    return session, laps, LinearDegradationModel.fit(laps)


@router.get("/sessions/{session_key}/degradation")
def degradation(session_key: int) -> dict:
    session, laps, model = fit_race(session_key)
    # Remove driver pace + fuel/track trend so points from all drivers line up per compound.
    driver = laps["driver"].map(model.driver_offset)
    laps = laps.assign(
        corrected_s=laps["lap_time_s"] - driver - model.lap_coef * laps["lap"],
        predicted_s=model.predict(laps),
    )
    curves = {}
    for compound, deg in model.deg_per_lap.items():
        ages = np.arange(1, int(laps.loc[laps.compound == compound, "tyre_life"].max()) + 1)
        curves[compound] = {
            "tyre_life": ages.tolist(),
            "corrected_s": (model.compound_offset[compound] + deg * ages).round(4).tolist(),
        }
    return {
        "session": session.name,
        "model": model.to_dict(),
        "curves": curves,
        "cliffs": cliff_ages(laps, model),
        "laps_per_compound": laps["compound"].value_counts().to_dict(),
        "points": records(
            laps[
                [
                    "driver",
                    "team",
                    "lap",
                    "stint",
                    "compound",
                    "tyre_life",
                    "lap_time_s",
                    "corrected_s",
                    "predicted_s",
                ]
            ].round(4)
        ),
    }


@router.get("/sessions/{session_key}/pace-model")
def pace_model(session_key: int) -> dict:
    """Multi-race model's expected pace by tyre age for this race's circuit and compounds."""
    try:
        model = load_model()
    except PaceModelMissingError as e:
        raise HTTPException(503, str(e)) from e
    session, laps, _ = fit_race(session_key)
    circuit = str(session.info["circuit_short_name"])
    max_age = {str(c): int(a) for c, a in laps.groupby("compound")["tyre_life"].max().items()}
    known = circuit in model.categories["circuit"]
    return {
        "circuit": circuit,
        # an unseen circuit falls back to the model's average circuit
        "circuit_in_training": known,
        "curves": tyre_curves(model, circuit, session.total_laps, max_age),
        "metrics": {
            k: v for k, v in model.metrics.items() if isinstance(v, int | float | str | list)
        },
    }
