"""Train the race predictor on Jolpica history and save it to models/race_predictor.joblib.

python scripts/train_race_predictor.py            # up to the current season
python scripts/train_race_predictor.py --mlflow   # also log the CV metrics to MLflow
"""

import argparse
import datetime as dt
import json
import logging

from pitwall.predict.service import FIRST_YEAR, train_and_save


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--last-year", type=int, default=dt.date.today().year)
    ap.add_argument("--mlflow", action="store_true")
    args = ap.parse_args()

    bundle = train_and_save(args.last_year)
    metrics = {name: p.metrics for name, p in bundle["predictors"].items()}
    print(json.dumps(metrics, indent=2))

    if args.mlflow:
        from pitwall.tracking import setup_mlflow

        mlflow = setup_mlflow("race-predictor")
        for name, predictor in bundle["predictors"].items():
            with mlflow.start_run(run_name=f"{name}-{FIRST_YEAR}-{args.last_year}"):
                mlflow.log_params(
                    {
                        "variant": name,
                        "features": ",".join(predictor.features),
                        "n_races": bundle["n_races"],
                    }
                )
                mlflow.log_metrics({**predictor.metrics, "temperature": predictor.temperature})


if __name__ == "__main__":
    main()
