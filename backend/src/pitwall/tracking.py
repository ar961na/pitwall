"""MLflow setup shared by all training scripts.

Runs go to a SQLite DB + artifact folder at the repo root. Browse them with:
    mlflow ui --backend-store-uri sqlite:///mlflow.db      (from the repo root)
"""

import os

from pitwall.config import REPO_ROOT


def setup_mlflow(experiment: str):
    import mlflow

    uri = os.environ.get("MLFLOW_TRACKING_URI", f"sqlite:///{REPO_ROOT / 'mlflow.db'}")
    mlflow.set_tracking_uri(uri)
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=(REPO_ROOT / "mlartifacts").as_uri())
    mlflow.set_experiment(experiment)
    return mlflow
