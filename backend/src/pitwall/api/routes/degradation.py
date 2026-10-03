import numpy as np
from fastapi import APIRouter, HTTPException

from pitwall.api.utils import get_session, records
from pitwall.data.laps import green_flag_laps, race_laps
from pitwall.models.tyre_deg import LinearDegradationModel

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
