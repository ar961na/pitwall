"""One-lap-ahead stint forecasts from the GRU [M24]. Needs the optional `dl` extra (PyTorch)."""

from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from pitwall.api.routes.degradation import fit_race
from pitwall.api.utils import records
from pitwall.config import settings
from pitwall.models.pace_gbm import add_target

router = APIRouter(tags=["degradation"])

UNAVAILABLE = (
    "The stint forecaster is not available on this server: it needs PyTorch (the `dl` extra) "
    "and a trained model (`make train-stint`)."
)


@lru_cache(maxsize=2)
def _load(path: Path, mtime: float):
    from pitwall.dl.stint_model import load_forecaster

    return load_forecaster(path)


def forecaster():
    try:
        from pitwall.dl.stint_model import MODEL_FILE
    except ImportError as e:  # no torch in this install
        raise HTTPException(503, UNAVAILABLE) from e
    path = settings.models_dir / MODEL_FILE
    if not path.exists():
        raise HTTPException(503, UNAVAILABLE)
    return _load(path, path.stat().st_mtime)


@router.get("/sessions/{session_key}/stint-forecast")
def stint_forecast(session_key: int, driver: str = Query(..., description="Driver code")) -> dict:
    """GRU one-lap-ahead forecasts against actual lap times, for one driver's stints."""
    model = forecaster()  # 503 before touching torch when it is not installed
    from pitwall.dl.stint_model import backtest

    session, laps, _ = fit_race(session_key)
    laps = laps[laps["driver"] == driver.upper()]
    if laps.empty:
        raise HTTPException(404, f"No green-flag laps for {driver} in {session.name}")
    out = backtest(model, add_target(laps.assign(session_key=session_key)))
    mae = {
        k: round(float((out[k] - out["actual"]).abs().mean()), 3) if len(out) else None
        for k in ("gru", "persistence")
    }
    until = str(model.metrics.get("train_until", ""))
    started = pd.Timestamp(session.info["date_start"])
    in_training = bool(until) and started <= pd.Timestamp(until)
    return {
        "session": session.name,
        "in_training_data": in_training,
        "driver": driver.upper(),
        "mae": mae,
        "model": model.metrics,
        "laps": records(out.round(4)),
    }
