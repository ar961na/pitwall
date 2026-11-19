# Roadmap

## Done

- Data layer on OpenF1, Jolpica and MultiViewer with a throttled disk cache
- Telemetry: distance-aligned lap comparison, minisector map, corner-by-corner table; on circuits
  without a published corner list, braking zones detected in the speed trace
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
  with that range, and strategy calibration takes its degradation rate for compounds whose
  race fit is missing or implausible. Its compound offsets are not used: it barely separates
  compounds' fresh-tyre pace (within 0.15 s), since compound choice is tied up with strategy
- Stint forecaster: GRU over the last 8 laps predicting the next 3. On the latest 20% of races:
  MAE 0.434 s vs 0.500 s for repeating the last lap and 0.666 s for a straight-line trend.
  The Tyres page shows its next-lap forecasts for a selected driver; per driver it is often
  level with repeating the last lap, so the gain is a fleet-wide average
- CI/CD: tests, type checks, Docker smoke test, GitHub Pages demo, GHCR images

## Next

1. Compare the stint forecaster with the pace model on the same future laps
2. Race predictor: weather and sprint-weekend features; a season scoreboard of past forecasts
3. Dependabot: config trimmed (on the PR branch); merge #20, #15 and #4 (TypeScript 7) separately
