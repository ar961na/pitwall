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
- CI/CD: tests, type checks, Docker smoke test, GitHub Pages demo, GHCR images

## Next

1. Multi-race LightGBM pace model with quantile intervals, compared with the per-race linear model
2. Stint sequence model (PyTorch) compared with persistence and the pace model
4. Race predictor: weather and sprint-weekend features; a season scoreboard of past forecasts
5. Triage the open Dependabot PRs (several are major version bumps)
