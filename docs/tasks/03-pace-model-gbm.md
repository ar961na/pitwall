# Task 3: Multi-race pace model (LightGBM)

**File:** `backend/src/pitwall/models/pace_gbm.py` → `build_pace_dataset()`, `time_series_splits()`;
add a `scripts/train_pace_gbm.py`
**Check:** `pytest -m task tests/tasks/test_task3_splits.py` (the splitter); the model is judged by your CV report.

## Goal

One model across many races that predicts a lap's pace from tyre compound, tyre age, fuel and
track state, with honest validation and uncertainty bands. This is "Tyre degradation & pace
prediction" from your project idea.

## Steps

1. **Dataset:** for every race in `years`, `green_flag_laps(race_laps(session))`, then add
   `year`, `round`, `circuit`, and the target `lap_time_delta_s = lap_time_s − median(driver,
   race)`. The first run is slow because of OpenF1's rate limit (~15 s per race), but the cache
   makes later runs instant. Save to `data/pace_<years>.parquet`.
2. **Splitter:** `time_series_splits(df, n_splits)` yields (train_idx, test_idx) as **positional**
   indices. Every test race comes after every train race, a race never ends up on both sides,
   and the train window grows (expanding window).
3. **Baselines first:** predict 0, then the linear model per race. Your GBM has to beat these.
4. **LightGBM:** `compound` as a categorical feature. Try `objective="regression"`, then
   `"huber"` (lap times have fat tails: traffic, mistakes).
5. **Uncertainty:** train two extra models with `objective="quantile", alpha=0.1 / 0.9`. Check
   **coverage**: does ~80% of the test laps land inside [q10, q90]?
6. **Track it:** copy the MLflow pattern from `scripts/fit_degradation.py` (`setup_mlflow`).
   Log params, per-fold MAE and coverage, and a feature-importance plot.

## Concept refresher

- **Why not `KFold(shuffle=True)`?** Laps of the same race are strongly correlated. A random split
  puts lap 20 in train and lap 21 in test, so the model "remembers" the race and the score lies.
  In production you always predict a *future* race.
- **Grouped + temporal:** split on `year*100 + round`, never on rows.
- **Quantile loss:** the pinball loss is minimised by the α-quantile of the target distribution.

<details><summary>Hint: splitter</summary>

`races = np.sort(key.unique())`, then `np.array_split(races, n_splits + 1)`. Fold *i* trains on
chunks `[:i]` and tests on chunk `i`. Return `np.flatnonzero(key.isin(...))` so the indices are
positional even when the frame is shuffled.
</details>

<details><summary>Hint: features worth trying</summary>

`tyre_life`, `compound`, `laps_remaining` (fuel proxy), `lap / total_laps`, `fresh_tyre`, circuit
(categorical), track temperature (OpenF1 `weather`, which needs an `openf1.get("weather", ...)`
join on time), `tyre_life × compound` (trees find interactions, but monotone constraints can
help: `monotone_constraints` on tyre_life = +1).
</details>

## Stretch

- Mixed-effects model (`statsmodels` MixedLM) with random intercepts per driver-race: compare
  with the GBM on the same folds.
- Use the GBM inside the simulator: implement a `PaceModel` interface so `clean_lap_times` can
  call either the parametric curve or the GBM.

## Interview questions

- Your random-KFold MAE was 0.15 s and your time-series MAE is 0.31 s. Which do you report, and why?
- How do you know your 80% intervals are calibrated?

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [D1] OpenF1 laps/stints/weather
- [M9] LightGBM (Ke et al. 2017), [M10] quantile regression (Koenker & Bassett 1978), [M11] Huber loss, [M12] mixed models (Bates et al. 2015), [M13] time-series CV (Bergmeir & Benítez 2012; Hyndman & Athanasopoulos §5.10)
