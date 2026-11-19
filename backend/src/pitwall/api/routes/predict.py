from fastapi import APIRouter, HTTPException

from pitwall.predict import service

router = APIRouter(tags=["predict"])


@router.get("/predict/{year}")
def rounds(year: int) -> list[dict]:
    """Rounds of a season and whether each is finished, qualified or upcoming."""
    try:
        return service.rounds(year)
    except Exception as e:  # upstream data problems
        raise HTTPException(502, f"Could not load the {year} calendar: {e}") from e


@router.get("/predict/{year}/{rnd}")
def predict(year: int, rnd: int) -> dict:
    """Finishing-order forecast with win and podium probabilities for one round."""
    try:
        return service.predict_round(year, rnd)
    except service.ModelMissingError as e:
        raise HTTPException(503, str(e)) from e
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
