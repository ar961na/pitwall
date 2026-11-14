# pitwall: notes for Claude

Follow ~/Work/references/AI_CONTEXT.md. Scope: `guidelines/ui.md` and `ui/tokens.css` for the
frontend (copied verbatim to `frontend/src/styles/tokens.css`; fixes go in `index.css`, marked).
`latex/` and `guidelines/latex-figures.md` are for LaTeX documents only, never the web app.

pitwall is a finished application, not a teaching scaffold (the owner changed this on
2026-11-14): implement features fully, with tests. Remaining unfinished pieces are listed in
`docs/ROADMAP.md`; update it when something lands.

## Citations

Every data source and method is listed in `docs/REFERENCES.md` with a tag (`[D1]`, `[M7]`) and
cited in module docstrings. When adding a data source, method, paper or magic number, add or
reuse a tag and cite it. Never present an assumed number as measured; label defaults as
illustrative.

## Layout

- `backend/src/pitwall/`: `data/` (OpenF1 + HTTP cache), `telemetry/`, `models/`, `strategy/`
  (Monte Carlo simulator), `predict/` (Jolpica history), `dl/`, `api/` (FastAPI, routes keyed by
  OpenF1 `session_key`)
- `frontend/`: React + TS + Vite + recharts; `src/hooks/useApi.ts` is the data-fetching pattern
- `docs/REFERENCES.md` (sources and methods), `docs/ROADMAP.md` (what is done and what is next)

## Commands

- Env: `micromamba activate pitwall` (Python 3.12, Node 22, PyTorch with MPS, LightGBM; both from
  conda-forge so they share one OpenMP runtime)
- `make api` / `make web` / `make test` / `make lint` / `make up` (Docker)
- Network tests: `pytest -m network`. OpenF1's free tier is 30 req/min, and the client throttles
  and caches under `data/http_cache`.

## CI/CD and the static demo

- `.github/workflows/ci.yml` gates everything; `pages.yml` and `images.yml` run only after green
  CI on main. Validate workflow edits with `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint`.
- The GitHub Pages build is the React app with `VITE_STATIC_DEMO=true`, reading JSON written by
  `python -m pitwall.static_demo`. File naming lives in two places that must agree:
  `static_path`/`optimize_path` (backend/src/pitwall/static_demo.py) and
  `staticPath`/`optimizePath` (frontend/src/api/static.ts). Shared test vectors guard this.
- A new endpoint the UI calls must also be added to `static_demo.build()`, or the demo shows
  "not included in the static demo".
- `scripts/smoke.sh` is the end-to-end check (`make smoke` after `make up`).

## Gotchas

- F1's live-timing archive (used by FastF1) returns 403 on this network, so don't reintroduce
  FastF1 as a runtime dependency.
- MultiViewer has no circuit info for brand-new tracks (404), so corners can be empty.
- MLflow ≥ 3 refuses the plain-folder store; use `pitwall.tracking.setup_mlflow` (SQLite).
