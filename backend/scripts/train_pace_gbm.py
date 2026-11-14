"""Train the multi-race pace model and save it to models/pace_gbm.joblib.

    python scripts/train_pace_gbm.py --years 2023 2024 2025 2026
The lap table is cached at data/pace_<first>_<last>.parquet; the first build takes about 15 s
per race because of the OpenF1 rate limit.
"""

import argparse
import datetime as dt
import json
import logging

import joblib
import pandas as pd

from pitwall.config import settings
from pitwall.models.pace_gbm import PaceModel, build_pace_dataset, evaluate

log = logging.getLogger("train_pace_gbm")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--years", type=int, nargs="+", default=[2023, 2024, 2025, 2026])
    ap.add_argument("--rebuild", action="store_true", help="ignore the cached lap table")
    ap.add_argument("--mlflow", action="store_true")
    args = ap.parse_args()

    table = settings.data_dir / f"pace_{min(args.years)}_{max(args.years)}.parquet"
    if table.exists() and not args.rebuild:
        df = pd.read_parquet(table)
    else:
        df = build_pace_dataset(args.years)
        table.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(table)
    df = df.sort_values(["year", "round"]).reset_index(drop=True)
    log.info(
        "%d laps, %d races, %d circuits",
        len(df),
        df["session_key"].nunique(),
        df["circuit"].nunique(),
    )

    metrics = evaluate(df)
    model = PaceModel.fit(df)
    model.metrics = {
        **metrics,
        "n_laps": len(df),
        "n_races": int(df["session_key"].nunique()),
        "years": [min(args.years), max(args.years)],
        "trained_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }
    out = settings.models_dir / "pace_gbm.joblib"
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out)
    print(json.dumps(model.metrics, indent=2))
    log.info("saved %s", out)

    if args.mlflow:
        from pitwall.tracking import setup_mlflow

        mlflow = setup_mlflow("pace-gbm")
        with mlflow.start_run(run_name=f"pace-{min(args.years)}-{max(args.years)}"):
            mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, int | float)})


if __name__ == "__main__":
    main()
