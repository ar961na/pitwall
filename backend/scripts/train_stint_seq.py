"""TASK 6 — train a sequence model that forecasts the next laps of a stint.

Skeleton only: the TODOs are yours (docs/tasks/06-sequence-model.md).

    python scripts/train_stint_seq.py --years 2023 2024 --epochs 30
"""

from __future__ import annotations

import argparse

import torch
from torch import nn

from pitwall.dl.device import best_device


class StintForecaster(nn.Module):
    """TODO: an LSTM/GRU (or small Transformer) mapping (B, context, F) -> (B, horizon)."""

    def __init__(self, n_features: int, horizon: int, hidden: int = 64):
        super().__init__()
        raise NotImplementedError("TASK 6")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        raise NotImplementedError("TASK 6")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=int, nargs="+", default=[2023, 2024])
    ap.add_argument("--context", type=int, default=8)
    ap.add_argument("--horizon", type=int, default=3)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--lr", type=float, default=1e-3)
    args = ap.parse_args()

    device = best_device()
    print(f"training on {device} with {vars(args)}")

    # TODO 1: build the stint table (build_pace_dataset from TASK 3 + a stint_id column),
    #         split by RACE in time (time_series_splits) — never randomly by window.
    # TODO 2: make_windows(...) for train/val; normalise features with TRAIN statistics only.
    # TODO 3: DataLoaders, model, AdamW, MSE (or Huber) loss, early stopping on val loss.
    # TODO 4: compare against baselines on the same val windows:
    #           (a) "persistence": next laps = last observed lap
    #           (b) your LightGBM pace model from TASK 3
    # TODO 5: log params, curves and the final model to MLflow (see scripts/fit_degradation.py).
    raise NotImplementedError("TASK 6")


if __name__ == "__main__":
    main()
