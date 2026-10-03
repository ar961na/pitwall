"""Runtime settings. Override any field with an env var, e.g. PITWALL_DATA_DIR=/data."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/src/pitwall/config.py -> repo root (only meaningful for the editable dev install)
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PITWALL_", env_file=".env", extra="ignore")

    data_dir: Path = REPO_ROOT / "data"
    models_dir: Path = REPO_ROOT / "models"
    cors_origins: list[str] = ["http://localhost:5173"]

    @property
    def fastf1_cache(self) -> Path:
        return self.data_dir / "fastf1_cache"


settings = Settings()
