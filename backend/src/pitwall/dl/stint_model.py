"""GRU forecaster for the next laps of a stint, with the baselines it has to beat.

The network sees the last CONTEXT laps of a stint and predicts the change in lap-time delta
over the next HORIZON laps relative to the last observed lap. Predicting the change, not the
level, makes "repeat the last lap" (persistence) the zero prediction, so any skill the model
shows is skill beyond persistence.

Method (docs/REFERENCES.md): GRU encoder [M24], Huber loss [M11], AdamW [M26], race-ordered
train/validation split [M13]. Needs the optional `dl` extra (PyTorch).
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn

from pitwall.dl.device import best_device
from pitwall.dl.stint_dataset import SEQ_FEATURES, make_windows
from pitwall.models.pace_gbm import TARGET

log = logging.getLogger(__name__)

CONTEXT = 8
HORIZON = 3
VAL_FRACTION = 0.2  # last 20% of races, in time order, for validation and early stopping
LINEAR_FIT_LAPS = 5  # laps used by the linear-extrapolation baseline


def stint_frame(laps: pd.DataFrame) -> pd.DataFrame:
    """Add compound one-hots and a `stint_id` that also splits stints where laps are missing.

    Green-flag filtering drops safety-car and outlier laps, so a stint can have holes; a window
    across a hole would mix laps that are not consecutive.
    """
    df = laps.sort_values(["session_key", "driver", "stint", "lap"]).reset_index(drop=True)
    for c in ("soft", "medium", "hard"):
        df[f"compound_{c}"] = (df["compound"].str.lower() == c).astype(float)
    base = df["stint_id"] if "stint_id" in df else df["session_key"].astype(str)
    new_stint = base.ne(base.shift())
    gap = df["lap"].diff().ne(1)
    df["stint_id"] = (new_stint | gap).cumsum().astype(str)
    return df


class StintForecaster(nn.Module):
    """GRU over the context laps; a linear head maps the last hidden state to HORIZON outputs."""

    def __init__(self, n_features: int, horizon: int = HORIZON, hidden: int = 64, layers: int = 1):
        super().__init__()
        self.gru = nn.GRU(n_features, hidden, num_layers=layers, batch_first=True)
        self.head = nn.Linear(hidden, horizon)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, h = self.gru(x)
        return self.head(h[-1])


@dataclass
class Scaler:
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "Scaler":
        flat = x.reshape(-1, x.shape[-1])
        std = flat.std(axis=0)
        return cls(flat.mean(axis=0), np.where(std > 0, std, 1.0))

    def __call__(self, x: np.ndarray) -> np.ndarray:
        return ((x - self.mean) / self.std).astype(np.float32)


@dataclass
class TrainedForecaster:
    model: StintForecaster
    scaler: Scaler
    metrics: dict[str, Any] = field(default_factory=dict)

    def predict(self, x: np.ndarray) -> np.ndarray:
        """Future lap-time deltas (n_windows, HORIZON) for raw context windows."""
        self.model.eval()
        with torch.no_grad():
            change = self.model(torch.from_numpy(self.scaler(x))).numpy()
        return change + _last_delta(x)[:, None]


def _last_delta(x: np.ndarray) -> np.ndarray:
    return x[:, -1, SEQ_FEATURES.index(TARGET)]


def persistence(x: np.ndarray, horizon: int = HORIZON) -> np.ndarray:
    """Every future lap equals the last observed one."""
    return np.repeat(_last_delta(x)[:, None], horizon, axis=1)


def linear_extrapolation(
    x: np.ndarray, horizon: int = HORIZON, k: int = LINEAR_FIT_LAPS
) -> np.ndarray:
    """Straight line through the last `k` laps, continued `horizon` laps ahead."""
    y = x[:, -k:, SEQ_FEATURES.index(TARGET)]
    t = np.arange(k, dtype=float)
    slope = ((t - t.mean()) * (y - y.mean(axis=1, keepdims=True))).sum(axis=1) / (
        (t - t.mean()) ** 2
    ).sum()
    intercept = y.mean(axis=1) - slope * t.mean()
    ahead = np.arange(k, k + horizon, dtype=float)
    return intercept[:, None] + slope[:, None] * ahead[None, :]


def race_split(
    df: pd.DataFrame, val_fraction: float = VAL_FRACTION
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Earlier races for training, the last `val_fraction` of races for validation."""
    race = df["year"] * 100 + df["round"]
    races = np.sort(race.unique())
    cut = races[int(len(races) * (1 - val_fraction))]
    return df[race < cut], df[race >= cut]


def train(
    laps: pd.DataFrame,
    epochs: int = 40,
    lr: float = 1e-3,
    batch_size: int = 256,
    patience: int = 6,
    seed: int = 0,
    device: torch.device | None = None,
) -> TrainedForecaster:
    """Train on earlier races, early-stop on later ones, and report MAE against the baselines."""
    torch.manual_seed(seed)
    device = device or best_device()
    train_df, val_df = race_split(stint_frame(laps))
    x_tr, y_tr = make_windows(train_df, CONTEXT, HORIZON)
    x_va, y_va = make_windows(val_df, CONTEXT, HORIZON)
    if not len(x_tr) or not len(x_va):
        raise ValueError("Not enough consecutive laps for training and validation windows")
    scaler = Scaler.fit(x_tr)
    # targets are changes relative to the last observed lap (see module docstring)
    t_tr = (y_tr - _last_delta(x_tr)[:, None]).astype(np.float32)
    t_va = (y_va - _last_delta(x_va)[:, None]).astype(np.float32)

    model = StintForecaster(len(SEQ_FEATURES)).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = nn.HuberLoss(delta=1.0)
    xs, ts = torch.from_numpy(scaler(x_tr)), torch.from_numpy(t_tr)
    xv, tv = torch.from_numpy(scaler(x_va)).to(device), torch.from_numpy(t_va).to(device)

    best, best_state, stale, history = np.inf, None, 0, []
    for epoch in range(epochs):
        model.train()
        order = torch.randperm(len(xs))
        for i in range(0, len(xs), batch_size):
            idx = order[i : i + batch_size]
            opt.zero_grad(set_to_none=True)
            loss = loss_fn(model(xs[idx].to(device)), ts[idx].to(device))
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
        model.eval()
        with torch.no_grad():
            val = float(loss_fn(model(xv), tv))
        history.append(val)
        if val < best - 1e-5:
            best, stale = val, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if stale >= patience:
                break
        log.info("epoch %d  val huber %.4f", epoch + 1, val)

    model = model.cpu()
    if best_state is not None:
        model.load_state_dict(best_state)
    trained = TrainedForecaster(model, scaler)
    mae = {
        "gru": trained.predict(x_va),
        "persistence": persistence(x_va),
        "linear": linear_extrapolation(x_va),
    }
    trained.metrics = {
        **{f"mae_{k}_s": float(np.abs(v - y_va).mean()) for k, v in mae.items()},
        "n_train_windows": len(x_tr),
        "n_val_windows": len(x_va),
        "epochs": len(history),
        "best_val_huber": float(best),
        "device": str(device),
    }
    return trained
