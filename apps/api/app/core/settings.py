from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Find the repository root:
# settings.py -> core -> app -> api -> apps -> ResearchMind-AI
BASE_DIR = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_name: str = "ResearchMind"
    app_version: str = "0.1.0"
    environment: str = "development"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str
    valkey_url: str
    qdrant_url: str

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()