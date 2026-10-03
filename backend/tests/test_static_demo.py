"""Static-demo snapshot: file naming must match frontend/src/api/static.ts exactly."""

import json

import pytest

from pitwall.static_demo import build, optimize_path, static_path

# Same vectors are asserted in frontend/src/api/static.test.ts — change both together.
VECTORS = [
    ("/health", "health.json"),
    ("/events/2026", "events/2026.json"),
    ("/sessions/11361/drivers", "sessions/11361/drivers.json"),
    ("/sessions/11361/compare?a=VER&b=NOR", "sessions/11361/compare__a=VER__b=NOR.json"),
    ("/sessions/11361/compare?b=NOR&a=VER", "sessions/11361/compare__a=VER__b=NOR.json"),
    ("/sessions/9920/strategy/calibrate", "sessions/9920/strategy/calibrate.json"),
]


@pytest.mark.parametrize(("path", "expected"), VECTORS)
def test_static_path(path, expected):
    assert static_path(path) == expected


def test_optimize_path():
    assert optimize_path("calibrated-9920", 2, 2000) == (
        "strategy/optimize/calibrated-9920__stops2__sims2000.json"
    )


def test_build_offline_without_sessions(tmp_path):
    manifest = build(tmp_path / "out", keys=[], this_year=2024)
    out = tmp_path / "out"
    assert json.loads((out / "health.json").read_text())["status"] == "ok"
    assert json.loads((out / "events/2023.json").read_text()) == []
    assert (out / "strategy/defaults.json").exists()
    res = json.loads((out / optimize_path("defaults", 2, 2000)).read_text())
    assert res["results"][0]["gap_s"] == 0
    assert "CC BY-NC-SA 4.0" in (out / "README.txt").read_text()
    assert manifest["sessions"] == []
