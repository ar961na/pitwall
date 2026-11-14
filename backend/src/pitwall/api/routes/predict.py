from fastapi import APIRouter, HTTPException

from pitwall.config import settings

router = APIRouter(tags=["predict"])

MODEL_PATH = settings.models_dir / "race_predictor.joblib"


@router.get("/predict/{year}/{event}")
def predict(year: int, event: str) -> dict:
    """Pre-race finishing-order prediction (after qualifying)."""
    if not MODEL_PATH.exists():
        raise HTTPException(
            501,
            "No trained race predictor yet (see docs/ROADMAP.md)",
        )
    raise HTTPException(501, "Model file found but inference is not wired up yet")
