# Hands-on tasks

The infrastructure, data layer, baseline models, simulator, API and UI are done and tested.
The parts below are **yours**: each one is a stub that raises `NotImplementedError`, with
acceptance tests that fail until you implement it. Every task was checked against a private
reference solution, so all of them are passable.

```bash
cd backend
pytest -m task                                   # all task tests (expect failures to start)
pytest -m task tests/tasks/test_task1_corners.py # one task
```

Hints are hidden behind collapsible "Hint" blocks. Open one only after you've been stuck for
~20 minutes. When you're done, ask Claude to **review** your code rather than write it.

| # | Task | Skills | Feeds into | Est. |
|---|------|--------|-----------|------|
| [1](01-corner-analysis.md) | Corner-by-corner analysis | pandas, signal processing | Telemetry page table | 2–4 h |
| [2](02-tyre-degradation.md) | Fuel correction + cliff detection | regression, model selection, stats tests | Strategy simulator | 3–5 h |
| [3](03-pace-model-gbm.md) | Multi-race pace model (LightGBM) | feature eng., time-series CV, quantiles, MLflow | Strategy + Task 6 baseline | 1–2 days |
| [4](04-reactive-strategy.md) | Pit-under-safety-car policy | simulation, policies, variance reduction | Strategy page | 3–5 h |
| [5](05-race-predictor.md) | Finishing-order predictor (+ serve it) | leakage-free features, ranking, calibration, MLOps | Predict page, race weekends | 2–3 days |
| [6](06-sequence-model.md) | Stint forecaster (PyTorch on MPS) | DL: LSTM/Transformer, training loops, baselines | Compare with Task 3 | 2–3 days |
| [R1](R1-tyres-page.md) | Tyres page | React hooks, recharts | — | 3–5 h |
| [R2](R2-predict-page.md) | Predict page | React, API design | uses Task 5 | 3–5 h |

**Suggested order:** 1 → R1 → 2 → 4 → 3 → 5 → R2 → 6. Tasks 1 and R1 are warm-ups that
get you back into pandas and into React. Task 5 is the one to have ready for the next race
weekend.

## Citing as you go

Every data source and method used so far is listed in [docs/REFERENCES.md](../REFERENCES.md) with
a tag (`[D1]`, `[M7]`, …), and the code cites those tags in its docstrings. Keep doing that:
when you use a new method, paper, regulation or dataset, add an entry and cite the tag in your
code, notebook and journal. Interviewers notice.

## Ground rules for the collaboration

- You write the code inside the stubs. Claude can explain concepts, review diffs, and debug
  with you, and it writes infrastructure (new endpoints, wiring, CI).
- Commit each task on its own branch (`git switch -c task/1-corners`) and open a PR.
  Claude can review the PR like a teammate would.
- After each task, write 3–5 sentences in `docs/journal.md`: what you tried, what failed, and
  what you'd say about it in an interview. This becomes your blog post and README later.
