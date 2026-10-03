"""Fit the baseline tyre model on every race of a season and log each fit to MLflow.

This is the reference pattern for experiment tracking — copy it for your own models.

    python scripts/fit_degradation.py --year 2025
    mlflow ui --backend-store-uri sqlite:///mlflow.db     # from repo root, then http://localhost:5000
"""

from __future__ import annotations

import argparse
import logging

import pandas as pd

from pitwall.data import openf1
from pitwall.data.laps import green_flag_laps, race_laps
from pitwall.models.tyre_deg import LinearDegradationModel
from pitwall.tracking import setup_mlflow

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("fit_degradation")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    ap.add_argument("--max-races", type=int, default=None)
    args = ap.parse_args()

    mlflow = setup_mlflow("tyre-degradation-baseline")

    races = openf1.sessions(args.year)
    now = pd.Timestamp.now(tz="UTC")
    races = races[(races["session_name"] == "Race") & (races["date_start"] < now)]
    for row in races.head(args.max_races).itertuples():
        try:
            session = openf1.load_session(int(row.session_key))
            laps = green_flag_laps(race_laps(session))
            model = LinearDegradationModel.fit(laps)
        except Exception as e:  # wet races, missing data...
            log.warning("skip %s: %s", row.circuit_short_name, e)
            continue

        with mlflow.start_run(run_name=session.name):
            mlflow.log_params(
                {
                    "year": args.year,
                    "circuit": row.circuit_short_name,
                    "model": "linear",
                    "reference": model.reference_compound,
                }
            )
            mlflow.log_metrics(
                {
                    "rmse_s": model.rmse,
                    "n_laps": model.n_laps,
                    "lap_coef": model.lap_coef,
                    **{f"deg_{c}": v for c, v in model.deg_per_lap.items()},
                }
            )
            mlflow.log_dict(model.to_dict(), "model.json")
        log.info(
            "%-28s rmse=%.3f deg=%s",
            session.name,
            model.rmse,
            {c: round(v, 3) for c, v in model.deg_per_lap.items()},
        )


if __name__ == "__main__":
    main()
