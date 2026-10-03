"""Data provenance, served so every client can show the attribution the licences require."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["meta"])

SOURCES = [
    {
        "tag": "D1",
        "name": "OpenF1",
        "url": "https://openf1.org",
        "licence": "CC BY-NC-SA 4.0",
        "used_for": "sessions, laps, stints, pit stops, race control, car telemetry, positions",
    },
    {
        "tag": "D2",
        "name": "Jolpica F1 (Ergast-compatible)",
        "url": "https://github.com/jolpica/jolpica-f1",
        "licence": "CC BY-NC-SA 4.0",
        "used_for": "historical results and qualifying",
    },
    {
        "tag": "D3",
        "name": "MultiViewer circuit API",
        "url": "https://multiviewer.app",
        "licence": "unspecified (credited, as FastF1 does)",
        "used_for": "corner positions and typical pit loss",
    },
]
DISCLAIMER = (
    "Unofficial, non-commercial project; not associated with Formula 1. F1 and related marks "
    "are trade marks of Formula One Licensing B.V."
)


@router.get("/sources")
def sources() -> dict:
    return {"sources": SOURCES, "disclaimer": DISCLAIMER, "details": "docs/REFERENCES.md"}
