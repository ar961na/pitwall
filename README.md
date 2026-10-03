# pitwall 🏎️

[![CI](https://github.com/ar961na/pitwall/actions/workflows/ci.yml/badge.svg)](https://github.com/ar961na/pitwall/actions/workflows/ci.yml)
[![Demo](https://github.com/ar961na/pitwall/actions/workflows/pages.yml/badge.svg)](https://ar961na.github.io/pitwall/)
[![CodeQL](https://github.com/ar961na/pitwall/actions/workflows/codeql.yml/badge.svg)](https://github.com/ar961na/pitwall/actions/workflows/codeql.yml)

**Live demo: https://ar961na.github.io/pitwall/** (static snapshot, refreshed weekly; see [CI/CD](#cicd))

**An end-to-end F1 race-strategy toolkit:** telemetry comparison → tyre-degradation models →
Monte Carlo strategy optimiser → race-outcome prediction, served by a FastAPI backend and a
React dashboard.

```
OpenF1 [D1] ──► data layer (throttled, cached) ──► telemetry analysis ─────────────┐
   │                                          └──► tyre / pace models ──► strategy  │──► FastAPI ──► React UI
Jolpica [D2] ──► results history ──► race predictor (LightGBM → PyTorch, MLflow) ──┘
MultiViewer [D3] ──► corners, pit loss
```

| Page | What it does | Status |
|------|--------------|--------|
| **Telemetry** | Fastest lap of driver A vs B on a common distance grid: speed, throttle/brake, running delta, track map coloured by who's faster per minisector | ✅ (corner table: Task 1) |
| **Strategy** | Fit tyre degradation + pit loss to a real race, enumerate every legal 1–3 stop strategy, Monte-Carlo them with safety cars on common random numbers, rank by mean time and P(best) | ✅ (reactive SC policy: Task 4) |
| **Tyres** | Degradation per compound, fuel- and driver-corrected | API ✅, page: Task R1 |
| **Predict** | Finishing order + win/podium probabilities after qualifying | Tasks 5 + R2 |

## Quick start

### Option A: local (micromamba; uses the Apple-Silicon GPU for PyTorch)

```bash
micromamba create -f environment.yml -y
micromamba activate pitwall
make api      # http://localhost:8000/docs
make web      # http://localhost:5173  (second terminal)
```

### Option B: Docker

```bash
docker compose up --build    # http://localhost:8080
docker compose run --rm test # lint + tests in a container
```

The first load of a session takes ~15–20 s because OpenF1's free tier allows 30 requests/min.
After that, everything is served from `data/http_cache`, which both options share.

## Tests

```bash
make test           # offline unit tests (backend + frontend)
make test-tasks     # acceptance tests for the hands-on tasks
make test-network   # live checks against OpenF1 / Jolpica
```

## CI/CD

| Workflow | When | What it guarantees |
|----------|------|--------------------|
| [`ci.yml`](.github/workflows/ci.yml) | every push / PR | ruff + 33 offline tests on Python 3.11–3.13 with coverage; frontend lint, format, types, vitest, build (app + static demo); Docker build, tests inside the image, `docker compose up` + [end-to-end smoke test](scripts/smoke.sh) through nginx. Plus a non-blocking **task scoreboard** in the job summary. |
| [`pages.yml`](.github/workflows/pages.yml) | after green CI on `main`, Mondays 06:00 UTC, manual | **CD:** runs the real API against OpenF1 for a few showcase sessions (`python -m pitwall.static_demo`), builds the React app in static mode and deploys it to GitHub Pages |
| [`images.yml`](.github/workflows/images.yml) | after green CI on `main`, `v*` tags | **CD:** multi-arch (amd64/arm64) API + web images to `ghcr.io/ar961na/pitwall-{api,web}` |
| [`weekly.yml`](.github/workflows/weekly.yml) | Mondays, PRs touching the env | `environment.yml` still solves and passes the suite; live contract tests against OpenF1 / Jolpica |
| [`codeql.yml`](.github/workflows/codeql.yml) + [Dependabot](.github/dependabot.yml) | push / PR / weekly | security scanning; grouped weekly dependency updates |

**Why the demo is static:** GitHub Pages only serves files, and the backend is Python. So CI runs
the backend once and saves its JSON answers for the showcase sessions (latest race weekend,
Monza 2026, Zandvoort 2025). The site reads those files instead of `/api`. Picking other
sessions or editing simulator parameters needs the full app (`make api` + `make web`, or Docker).

## Hands-on tasks

The core ML pieces are deliberately left as tested stubs. See **[docs/tasks/](docs/tasks/README.md)**:
corner analysis, cliff detection, a multi-race LightGBM pace model with time-series CV and
quantile intervals, a reactive safety-car policy, a leakage-free race predictor served from the
API, and a PyTorch stint forecaster.

## Data sources

| | Source | Used for | Licence |
|-|--------|----------|---------|
| D1 | [OpenF1](https://openf1.org) | sessions, laps, stints, pits, race control, ~3.7 Hz car telemetry, XY positions (2023→) | CC BY-NC-SA 4.0 |
| D2 | [Jolpica F1](https://github.com/jolpica/jolpica-f1) (Ergast-compatible) | results + qualifying history (1950→) | CC BY-NC-SA 4.0 |
| D3 | [MultiViewer](https://multiviewer.app) circuit API | corner positions, typical pit loss | credited (as in FastF1) |

FastF1 isn't used at runtime: F1's live-timing archive it reads returned HTTP 403 on our
network (2026-10-03). Raw data is never committed to this repo.

## Methods (selection)

- **Lap comparison:** distance from integrated speed and resampling onto a common distance grid
  (FastF1-style) [M1–M3]
- **Tyre model:** fixed-effects least squares, after the lap-time decomposition of
  Heilmeier et al. (2018) [M5, M6]; breakpoint regression for the cliff [M7, M8]
- **Strategy:** lap-by-lap Monte Carlo race simulation after Heilmeier et al. (2020) [M17]
  with common random numbers for variance reduction [M18]
- **Prediction:** LightGBM [M9], LambdaMART ranking [M21], time-ordered CV [M13], leakage
  checks [M14], Brier score and calibration [M15, M16]; sequence models in PyTorch [M24–M26]

Full bibliography with DOIs and exactly where each item is used: **[docs/REFERENCES.md](docs/REFERENCES.md)**.

## Repository layout

```
backend/   FastAPI + pitwall package (data, telemetry, models, strategy, predict, dl), tests, scripts
frontend/  React + TypeScript + Vite + recharts
docs/      tasks/ (hands-on tasks with hints), REFERENCES.md
data/      HTTP cache (git-ignored)      models/  trained models (git-ignored)
```

## Disclaimer

Unofficial, non-commercial project; not associated in any way with the Formula 1 companies. F1,
FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade
marks of Formula One Licensing B.V. Code is MIT-licensed; data belongs to its providers (see above).
