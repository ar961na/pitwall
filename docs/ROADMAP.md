# Roadmap

## Done

- Data layer on OpenF1, Jolpica and MultiViewer with a throttled disk cache
- Telemetry: distance-aligned lap comparison, minisector map, corner-by-corner table
- Tyres: linear degradation model per race, cliff detection per stint (late-stint breakpoints only)
- Strategy: Monte Carlo optimiser, calibration from a real race (tyres, cliffs, pit loss),
  gain from reacting to safety cars
- Building blocks for the models below: multi-race pace dataset, race-ordered CV splits,
  leakage-free pre-race features, stint windows for sequence models
- CI/CD: tests, type checks, Docker smoke test, GitHub Pages demo, GHCR images

## Next

1. Tyres page in the web app (the API already serves the data)
2. Race predictor: train on Jolpica history, evaluate with race-ordered CV, serve from
   `/api/predict`, Predict page
3. Multi-race LightGBM pace model with quantile intervals, compared with the per-race linear model
4. Stint sequence model (PyTorch) compared with persistence and the pace model
5. Reactive policy as an option in the Strategy page ranking, not only a reported gain
