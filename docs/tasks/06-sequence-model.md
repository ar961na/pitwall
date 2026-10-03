# Task 6: Stint forecaster in PyTorch (Apple GPU)

**Files:** `backend/src/pitwall/dl/stint_dataset.py` → `make_windows()`;
`backend/scripts/train_stint_seq.py` (the skeleton with TODOs)
**Check:** `pytest -m task tests/tasks/test_task6_windows.py`; the model is judged against baselines.
**Prereq:** Task 3 (`build_pace_dataset`, `time_series_splits`).

## Goal

Given the last `context` laps of a stint, forecast the next `horizon` lap-time deltas. Can a
sequence model see the cliff coming earlier than the GBM? This is the "go deeper into DL" task.

## Steps

1. `make_windows` (tested): sliding windows *within* each stint, float32.
2. Data split **by race in time**, then build the windows. Never split windows randomly: overlapping
   windows from one stint in both train and val is leakage again.
3. Normalise features with train-set mean/std only (save them with the model).
4. Model: start with `nn.GRU(n_features, 64, batch_first=True)` → last hidden → `nn.Linear(64,
   horizon)`. Then try an LSTM, a 1-D CNN, and a tiny Transformer encoder with learned
   positional embeddings.
5. Training loop by hand (no Lightning yet): AdamW, Huber loss, gradient clipping, early stopping
   on val loss, and checkpoint the best epoch. `pitwall.dl.device.best_device()` gives you `mps`.
6. **Baselines on the same val windows:** persistence (repeat the last lap), linear extrapolation
   of the last k laps, your Task 3 GBM. If the net can't beat persistence, report that honestly.
   That's a result too.
7. MLflow: log the config, per-epoch curves, the best checkpoint, and a plot of forecast vs actual
   for a few stints.

## Concept refresher (PyTorch)

```python
model.train()
for xb, yb in loader:
    xb, yb = xb.to(device), yb.to(device)
    opt.zero_grad(set_to_none=True)
    loss = loss_fn(model(xb), yb)
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()
model.eval()
with torch.no_grad(): ...
```

- **MPS notes:** use float32 (no float64 on MPS). Small models can be *slower* on GPU than CPU
  because of launch overhead, so time both and say which you chose and why.
- **Direct multi-horizon output** (one head predicting `horizon` steps) vs **autoregressive**
  (feed predictions back in): know the trade-off (error accumulation vs flexibility).

<details><summary>Hint: make_windows</summary>

`for _, g in stints.groupby("stint_id", sort=False)` → `a = g[SEQ_FEATURES].to_numpy(np.float32)`,
`t = g["lap_time_delta_s"].to_numpy(np.float32)`, then
`for s in range(len(g) - context - horizon + 1): X.append(a[s:s+context]); y.append(t[s+context:s+context+horizon])`.
Handle "no windows at all" by returning correctly-shaped empty arrays.
</details>

## Stretch

- Probabilistic output: predict mean and log-variance (Gaussian NLL), or quantiles. Compare
  calibration with your LightGBM quantiles.
- Condition on the driver with a learned embedding, then plot the embedding space (t-SNE/PCA).
  Do tyre-whisperers cluster?
- Export with `torch.export` / ONNX and serve it from the API (the Docker image would need the `dl`
  extra; CPU inference is fine).

## References

Tags point to [docs/REFERENCES.md](../REFERENCES.md).

- [D1] OpenF1 laps/stints
- [M24] LSTM (Hochreiter & Schmidhuber 1997), GRU (Cho et al. 2014), [M25] Transformer (Vaswani et al. 2017), [M26] AdamW (Loshchilov & Hutter 2019), [M11] Huber loss, [M13] time-ordered splits
- PyTorch MPS backend notes: https://pytorch.org/docs/stable/notes/mps.html
