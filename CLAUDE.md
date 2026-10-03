# pitwall: notes for Claude

This is a **collaborative learning project**. The owner is preparing for F1 data/ML roles and
wants to be able to explain every line in an interview.

## The one rule

Functions that raise `NotImplementedError("TASK …")` and the TODOs in
`backend/scripts/train_stint_seq.py` and `frontend/src/pages/{Tyres,Predict}Page.tsx` are the
**owner's tasks** (see `docs/tasks/`). Don't implement them, even if asked casually. Instead:
explain concepts, point to the relevant hint, review their attempt, run the task tests
(`pytest -m task …`), and debug *with* them. Writing infrastructure (endpoints, wiring, CI,
Docker, data plumbing) is fine. If the owner explicitly says "write it for me", confirm once,
because that's their call.

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
- `docs/tasks/`: task sheets with hidden hints; `docs/REFERENCES.md`

## Commands

- Env: `micromamba activate pitwall` (Python 3.12, Node 22, PyTorch with MPS, LightGBM; both from
  conda-forge so they share one OpenMP runtime)
- `make api` / `make web` / `make test` / `make test-tasks` / `make lint` / `make up` (Docker)
- Network tests: `pytest -m network`. OpenF1's free tier is 30 req/min, and the client throttles
  and caches under `data/http_cache`.

## Gotchas

- F1's live-timing archive (used by FastF1) returns 403 on this network, so don't reintroduce
  FastF1 as a runtime dependency.
- MultiViewer has no circuit info for brand-new tracks (404), so corners can be empty.
- MLflow ≥ 3 refuses the plain-folder store; use `pitwall.tracking.setup_mlflow` (SQLite).
