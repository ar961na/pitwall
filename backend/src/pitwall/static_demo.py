"""Build a static snapshot of the API for the GitHub Pages demo.

GitHub Pages can only serve files, so CI runs the real FastAPI app in-process (TestClient),
requests every endpoint the UI needs for a handful of featured sessions, and writes each JSON
response to a file whose name is derived from the request (`static_path`). The frontend, built
with VITE_STATIC_DEMO=true, reads those files instead of calling /api.

    python -m pitwall.static_demo --out ../frontend/public/static-api

The snapshot contains data derived from OpenF1 [D1] and MultiViewer [D3]; it is published under
the same CC BY-NC-SA 4.0 terms as OpenF1 (see docs/REFERENCES.md and the README.txt written next
to the files).
"""

import argparse
import itertools
import json
import logging
import shutil
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import pandas as pd
from fastapi.testclient import TestClient

from pitwall.api.main import app
from pitwall.data import openf1

log = logging.getLogger("static_demo")

FIRST_YEAR = 2023  # OpenF1 coverage starts here
# Fixed featured sessions (year, event, session name); the latest race weekend is added on top.
FEATURED = [
    (2026, "monza", "Race"),
    (2026, "monza", "Qualifying"),
    (2025, "zandvoort", "Race"),
]
OPTIMIZE_STOPS = (1, 2)
OPTIMIZE_SIMS = 2000  # must match the UI's default "Simulations" value

LICENCE_NOTE = """\
pitwall static demo data
========================
Derived from OpenF1 (https://openf1.org) and MultiViewer circuit info (https://multiviewer.app).
OpenF1 data is licensed CC BY-NC-SA 4.0; this derived snapshot is shared under the same licence
(https://creativecommons.org/licenses/by-nc-sa/4.0/). Non-commercial use only.
Unofficial project, not associated with Formula 1. Generated: {generated}
Code and full references: https://github.com/ar961na/pitwall (docs/REFERENCES.md)
"""


def static_path(path: str) -> str:
    """Request path -> relative file path. MUST match `staticPath` in frontend/src/api/static.ts.

    "/sessions/1/compare?b=NOR&a=VER" -> "sessions/1/compare__a=VER__b=NOR.json"
    """
    parts = urlsplit(path)
    base = parts.path.strip("/")
    if not parts.query:
        return f"{base}.json"
    return f"{base}__{'__'.join(sorted(parts.query.split('&')))}.json"


def optimize_path(label: str, max_stops: int, n_sims: int) -> str:
    """MUST match `optimizePath` in frontend/src/api/static.ts."""
    return f"strategy/optimize/{label}__stops{max_stops}__sims{n_sims}.json"


def latest_completed(year: int, session_name: str) -> int | None:
    df = openf1.sessions(year)
    if df.empty:
        return None
    done = df[
        (df["session_name"] == session_name)
        & (df["date_start"] + pd.Timedelta(hours=3) < pd.Timestamp.now(tz="UTC"))
    ]
    return int(done["session_key"].iloc[-1]) if not done.empty else None


def featured_keys(this_year: int) -> list[int]:
    keys: list[int] = []
    for name in ("Race", "Qualifying"):
        for year in (this_year, this_year - 1):
            key = latest_completed(year, name)
            if key:
                keys.append(key)
                break
    for year, event, name in FEATURED:
        try:
            keys.append(openf1.find_session(year, event, name))
        except ValueError as e:
            log.warning("featured %s %s %s unavailable: %s", year, event, name, e)
    return list(dict.fromkeys(keys))


class Writer:
    def __init__(self, client: TestClient, out: Path):
        self.client, self.out = client, out
        self.files = 0

    def save(self, rel: str, data) -> None:
        target = self.out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, separators=(",", ":")))
        self.files += 1

    def get(self, path: str):
        resp = self.client.get(f"/api{path}")
        if resp.status_code != 200:
            log.warning("skip %s: %s %s", path, resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        self.save(static_path(path), data)
        return data


def build(out: Path, keys: list[int] | None = None, this_year: int | None = None) -> dict:
    this_year = this_year or datetime.now(UTC).year
    keys = featured_keys(this_year) if keys is None else keys
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    w = Writer(TestClient(app), out)

    w.get("/health")
    w.get("/sources")
    defaults = w.get("/strategy/defaults")

    # Calendar, filtered down to the featured sessions so the pickers only offer what exists.
    for year in range(FIRST_YEAR, this_year + 1):
        resp = w.client.get(f"/api/events/{year}") if keys else None
        events = resp.json() if resp is not None and resp.status_code == 200 else []
        kept = []
        for ev in events:
            sessions = [s for s in ev["sessions"] if s["session_key"] in keys]
            if sessions:
                kept.append({**ev, "sessions": sessions})
        w.save(static_path(f"/events/{year}"), kept)

    sessions_meta = []
    for key in keys:
        drivers = w.get(f"/sessions/{key}/drivers") or []
        top = [d["code"] for d in drivers if d["position"]][:3]
        for a, b in itertools.permutations(top, 2):
            w.get(f"/sessions/{key}/compare?a={a}&b={b}")
        info = openf1.load_session(key).info
        name = f"{info['year']} {info['circuit_short_name']} {info['session_name']}"
        sessions_meta.append({"session_key": key, "name": name, "drivers": top})
        if info["session_name"] == "Race":
            w.get(f"/sessions/{key}/degradation")
            params = w.get(f"/sessions/{key}/strategy/calibrate")
            if params:
                _optimize(w, f"calibrated-{key}", params)

    if defaults:
        _optimize(w, "defaults", defaults)

    manifest = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "sessions": sessions_meta,
        "optimize": {"max_stops": list(OPTIMIZE_STOPS), "n_sims": OPTIMIZE_SIMS},
    }
    w.save("manifest.json", manifest)
    (out / "README.txt").write_text(LICENCE_NOTE.format(generated=manifest["generated_at"]))
    log.info("wrote %d files for %d sessions to %s", w.files, len(keys), out)
    return manifest


def _optimize(w: Writer, label: str, params: dict) -> None:
    for stops in OPTIMIZE_STOPS:
        body = {"params": params, "max_stops": stops, "min_stint": 8, "n_sims": OPTIMIZE_SIMS}
        resp = w.client.post("/api/strategy/optimize", json={**body, "seed": 0})
        if resp.status_code == 200:
            w.save(optimize_path(label, stops, OPTIMIZE_SIMS), resp.json())
        else:
            log.warning("skip optimize %s/%s: %s", label, stops, resp.status_code)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sessions", type=int, nargs="*", help="session keys (default: featured)")
    args = ap.parse_args()
    manifest = build(args.out, keys=args.sessions)
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
