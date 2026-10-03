# Task 5: Predict the race you're about to watch

**Files:** `backend/src/pitwall/predict/features.py` → `build_features()`; new
`scripts/train_race_predictor.py`; then wire `api/routes/predict.py`
**Check:** `pytest -m task tests/tasks/test_task5_features.py`
**Data:** `pitwall.predict.history.fetch_results(years)` (Jolpica: results + qualifying, back to 1950).

## Goal

After qualifying on Saturday, predict Sunday's finishing order with win/podium probabilities.
Log the prediction, watch the race, and score yourself.

## Steps

1. **Explore:** `df = fetch_results(list(range(2018, 2027)))`. How often does pole win? What's
   the Spearman correlation between grid and finish? That's your baseline to beat.
2. **Features (`build_features`):** see the docstring and tests. The no-leakage test changes the
   last race's results and asserts that *no earlier feature changes*.
3. **Model progression (log everything to MLflow):**
   1. Baseline: predicted finish = grid.
   2. LightGBM regression on finishing position.
   3. **LightGBM `LGBMRanker`** (`objective="lambdarank"`, `group=` drivers per race). Ranking is
      the natural formulation here.
   4. Win probability: Monte Carlo over the predicted scores with noise, or a softmax over the
      ranker scores calibrated on validation races (check a reliability diagram).
4. **Evaluation:** time-series CV by race (reuse your Task 3 splitter). Metrics: Spearman ρ,
   top-3 accuracy, winner log-loss, and **Brier score** for P(win).
5. **Serve it:** save the model + feature list with `joblib` to `models/race_predictor.joblib`
   and implement `GET /api/predict/{year}/{round}` (the stub returns 501 until the file exists).
   It fetches this weekend's qualifying, builds features, and returns rows of
   `{driver, grid, predicted_position, p_win, p_podium}`.
6. **Race weekend ritual:** run the prediction on Saturday night, commit the JSON to
   `predictions/2026-<round>.json`, and after the race run a scoring script that appends to
   `predictions/scores.csv`. A season-long track record is a great README chart.

## Concept refresher

- **Leakage** is the #1 way F1 predictors look amazing in notebooks and fail live. Rolling
  features need `.shift(1)` **before** `.rolling()`; "best finish at this track" must exclude the
  current season.
- **DNFs:** `position` is still set for retirements (classified last). Decide on a target:
  position, "finished in points", or position with DNFs treated separately. Each one is a
  modelling choice you should be able to defend.
- **Regulation changes** (2026 is a new era!) break history. Weight recent races more, or add
  "season" features.

<details><summary>Hint: rolling form without leakage</summary>

```python
df = df.sort_values(["year", "round"])
df["driver_form_pos"] = (df.groupby("driver_id")["position"]
                           .transform(lambda s: s.shift(1).rolling(5, min_periods=1).mean()))
```
Team form: first average per (team, race), then shift/roll per team, then merge back.
</details>

<details><summary>Hint: keeping row order</summary>

Compute on a sorted copy and finish with `results.merge(features, on=["year", "round",
"driver_id"], how="left")`. A left merge keeps the left frame's order.
</details>

## Stretch: deep learning

A **set/permutation model**: encode each driver (features → MLP), then let drivers attend to
each other (a single `nn.TransformerEncoder` layer, without positional encoding, since it's a
set) and output a score per driver. Train with a listwise loss (ListNet / Plackett–Luce
log-likelihood). Compare with LGBMRanker on the same folds.

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [D2] Jolpica (Ergast-compatible) results + qualifying, CC BY-NC-SA 4.0: credit it next to any published prediction
- [M13] time-ordered CV, [M14] leakage (Kaufman et al. 2012), [M15] Brier score, [M16] calibration (Niculescu-Mizil & Caruana 2005), [M21] LambdaMART (Burges 2010), [M22] ListNet / Plackett–Luce, [M23] Deep Sets / Set Transformer, [M25] Transformer
