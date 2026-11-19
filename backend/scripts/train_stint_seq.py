"""Train the GRU stint forecaster on the cached lap table and save models/stint_gru.pt.

python scripts/train_pace_gbm.py        # builds data/pace_<first>_<last>.parquet first
python scripts/train_stint_seq.py --years 2023 2026 --epochs 40
"""

import argparse
import json
import logging

import pandas as pd
import torch

from pitwall.config import settings
from pitwall.dl.stint_model import train


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--years", type=int, nargs=2, default=[2023, 2026], metavar=("FIRST", "LAST"))
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--lr", type=float, default=1e-3)
    # measured 2026-11-19: CPU 22 s vs Apple MPS 41 s for this small GRU (launch overhead)
    ap.add_argument("--gpu", action="store_true", help="use MPS/CUDA if available")
    args = ap.parse_args()

    table = settings.data_dir / f"pace_{args.years[0]}_{args.years[1]}.parquet"
    if not table.exists():
        raise SystemExit(f"{table} not found; run scripts/train_pace_gbm.py first")
    laps = pd.read_parquet(table)
    device = None if args.gpu else torch.device("cpu")
    model = train(laps, epochs=args.epochs, lr=args.lr, device=device)
    out = settings.models_dir / "stint_gru.pt"
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": model.model.state_dict(), "scaler": model.scaler, "metrics": model.metrics},
        out,
    )
    print(json.dumps(model.metrics, indent=2))


if __name__ == "__main__":
    main()
