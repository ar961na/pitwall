# Roadmap

## Done

- Data layer on OpenF1, Jolpica and MultiViewer with a throttled disk cache
- Telemetry: distance-aligned lap comparison, minisector map, corner-by-corner table
- Tyres: linear degradation model per race, cliff detection per stint (late-stint breakpoints only)
- Strategy: Monte Carlo optimiser, calibration from a real race (tyres, cliffs, pit loss),
  gain from reacting to safety cars, optional ranking with that reaction applied
- Building blocks for the models below: multi-race pace dataset, race-ordered CV splits,
  leakage-free pre-race features, stint windows for sequence models
- Race predictor: LambdaMART ranker with Plackett-Luce probabilities, pre- and post-qualifying
  variants, served from `/api/predict`, Predict page, included in the Pages demo. On 226
  held-out races it beats grid order on rank correlation (0.66 vs 0.62) and ties it on picking
  the winner (55%).
- Pace model: LightGBM quantile models across 89 races (2023-2026). On 65,234 held-out laps:
  MAE 0.606 s vs 0.618 s for a pooled linear model; the 80% interval, after conformal
  calibration, covers 82.8% (64% before). The Tyres page shows its expected pace by tyre age
  with that range
- Stint forecaster: GRU over the last 8 laps predicting the next 3. On the latest 20% of races:
  MAE 0.434 s vs 0.500 s for repeating the last lap and 0.666 s for a straight-line trend
- CI/CD: tests, type checks, Docker smoke test, GitHub Pages demo, GHCR images

## Next

1. Use the pace model and stint forecaster in strategy calibration (the Tyres page already shows
   the pace model)
2. Compare the stint forecaster with the pace model on the same future laps
3. Race predictor: weather and sprint-weekend features; a season scoreboard of past forecasts
4. Corner detection from speed minima for circuits without published corner data [M4]
5. Triage the open Dependabot PRs (several are major version bumps)
