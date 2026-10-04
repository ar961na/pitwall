# pitwall

[![CI](https://github.com/ar961na/pitwall/actions/workflows/ci.yml/badge.svg)](https://github.com/ar961na/pitwall/actions/workflows/ci.yml)
[![CodeQL](https://github.com/ar961na/pitwall/actions/workflows/codeql.yml/badge.svg)](https://github.com/ar961na/pitwall/actions/workflows/codeql.yml)

F1 race-strategy toolkit: compare two drivers' laps on telemetry, fit tyre degradation to a real
race, and search pit strategies with a Monte Carlo race simulator. A FastAPI backend serves it to a
React dashboard. Race-outcome prediction is in progress.

Demo: https://ar961na.github.io/pitwall/ (static snapshot of five sessions, rebuilt weekly; see
[why it is static](#cicd)).

```
OpenF1 [D1] ──► data layer (throttled, cached) ──► telemetry analysis ─────────────┐
   │                                          └──► tyre / pace models ──► strategy  │──► FastAPI ──► React UI
Jolpica [D2] ──► results history ──► race predictor (LightGBM, PyTorch, MLflow) ───┘
MultiViewer [D3] ──► corners, pit loss
```

| Page | What it does | Status |
|------|--------------|--------|
| Telemetry | Fastest lap of driver A vs B on a common distance grid: speed, throttle and brake, running delta, track map coloured by the faster driver per minisector | Working. Corner table is Task 1. |
| Strategy | Fits tyre degradation and pit loss to a real race, enumerates every legal 1 to 3 stop strategy, simulates them with random safety cars on common random numbers, ranks by mean race time and P(best) | Working. Reactive safety-car policy is Task 4. |
| Tyres | Degradation per compound, corrected for fuel and driver | API working. Page is Task R1. |
| Predict | Finishing order with win and podium probabilities after qualifying | Tasks 5 and R2 |

## Quick start

Local, with micromamba (PyTorch uses the Apple-Silicon GPU here):

```bash
micromamba create -f environment.yml -y
micromamba activate pitwall
make api      # http://localhost:8000/docs
make web      # http://localhost:5173  (second terminal)
```

Docker:

```bash
docker compose up --build    # http://localhost:8080
docker compose run --rm test # lint + tests in a container
```

The first load of a session takes 15 to 20 s because OpenF1's free tier allows 30 requests per
minute. Later loads come from `data/http_cache`, which both setups share.

## Tests

```bash
make test           # offline unit tests (backend + frontend)
make test-tasks     # acceptance tests for the hands-on tasks
make scoreboard     # task progress table
make test-network   # live checks against OpenF1 and Jolpica
```

## CI/CD

| Workflow | Runs on | Checks or does |
|----------|---------|----------------|
| [`ci.yml`](.github/workflows/ci.yml) | every push and PR | ruff and the offline test suite on Python 3.11, 3.12 and 3.13 with coverage; frontend lint, format, types, vitest and both builds; Docker build, tests inside the image, `docker compose up` and an [end-to-end smoke test](scripts/smoke.sh) through nginx; a task scoreboard in the job summary that never fails the build. On a push to `main`, after all of that passes, it deploys the demo and publishes images. |
| [`pages.yml`](.github/workflows/pages.yml) | called by CI on `main`, Mondays 06:00 UTC, manual | Runs the real API against OpenF1 for the featured sessions (`python -m pitwall.static_demo`), builds the React app in static mode, deploys to GitHub Pages |
| [`images.yml`](.github/workflows/images.yml) | called by CI on `main`, `v*` tags | Multi-arch (amd64, arm64) images `ghcr.io/ar961na/pitwall-api` and `pitwall-web` |
| [`weekly.yml`](.github/workflows/weekly.yml) | Mondays, PRs that touch the environment | `environment.yml` still solves and the suite passes in it; live contract tests against OpenF1 and Jolpica |
| [`codeql.yml`](.github/workflows/codeql.yml), [Dependabot](.github/dependabot.yml) | push, PR, weekly | Code scanning for Python, TypeScript and the workflows; grouped weekly dependency updates |

Why the demo is static: GitHub Pages only serves files, and the backend is Python. CI runs the
backend once and saves its JSON responses for the featured sessions (latest race and qualifying,
Monza 2026, Zandvoort 2025). The site reads those files instead of calling `/api`. Other
sessions and edited simulator parameters need the full app.

## Hands-on tasks

The core ML pieces are tested stubs for the repo owner to implement: corner analysis, cliff
detection, a multi-race LightGBM pace model with time-series CV and quantile intervals, a
reactive safety-car policy, a leakage-free race predictor served from the API, and a PyTorch stint
forecaster. See [docs/tasks/](docs/tasks/README.md).

## Data sources

| | Source | Used for | Licence |
|-|--------|----------|---------|
| D1 | [OpenF1](https://openf1.org) | sessions, laps, stints, pits, race control, car telemetry at about 3.7 Hz, XY positions (2023 onwards) | CC BY-NC-SA 4.0 |
| D2 | [Jolpica F1](https://github.com/jolpica/jolpica-f1) (Ergast-compatible) | results and qualifying history (1950 onwards) | CC BY-NC-SA 4.0 |
| D3 | [MultiViewer](https://multiviewer.app) circuit API | corner positions, typical pit loss | credited, as FastF1 does |

FastF1 is not used at runtime: the F1 live-timing archive it reads returned HTTP 403 on our
network on 2026-10-03. Raw data is never committed to this repo.

## Methods

- Lap comparison: distance from integrated speed, resampled onto a common distance grid, as in
  FastF1 [M1 to M3].
- Tyre model: least squares with driver fixed effects, after the lap-time decomposition of
  Heilmeier et al. (2018) [M5, M6]; breakpoint regression for the cliff [M7, M8].
- Strategy: lap-by-lap Monte Carlo race simulation after Heilmeier et al. (2020) [M17], with
  common random numbers for variance reduction [M18].
- Prediction: LightGBM [M9], LambdaMART ranking [M21], time-ordered CV [M13], leakage checks
  [M14], Brier score and calibration [M15, M16], sequence models in PyTorch [M24 to M26].

[docs/REFERENCES.md](docs/REFERENCES.md) has the full bibliography with DOIs and where each item is
used.

## Repository layout

```
backend/   FastAPI app and the pitwall package (data, telemetry, models, strategy, predict, dl)
frontend/  React, TypeScript, Vite, recharts
docs/      tasks/ (hands-on tasks with hints), REFERENCES.md
scripts/   smoke test
data/      HTTP cache (git-ignored)      models/  trained models (git-ignored)
```

## Disclaimer

Unofficial, non-commercial project, not associated with the Formula 1 companies. F1, FORMULA ONE,
FORMULA 1, FIA FORMULA ONE WORLD CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of
Formula One Licensing B.V. The code is MIT-licensed; the data belongs to its providers.
