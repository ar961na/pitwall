"""FastAPI app. Run locally with:  uvicorn pitwall.api.main:app --reload"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pitwall import __version__
from pitwall.api.routes import degradation, events, predict, sources, strategy, telemetry
from pitwall.config import settings

app = FastAPI(title="pitwall", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": __version__}


for module in (events, telemetry, degradation, strategy, predict, sources):
    app.include_router(module.router, prefix="/api")
