# Contains application configuration values.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration.

    Values are loaded from the local `.env` file during development
    and from environment variables in production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Application
    # ==========================================================================

    app_name: str = "ResearchMind AI"
    environment: str = "development"
    debug: bool = True

    # ==========================================================================
    # Database
    # ==========================================================================

    database_url: str = Field(...)
    valkey_url: str = Field(...)
    qdrant_url: str = Field(...)

    # ==========================================================================
    # Frontend
    # ==========================================================================

    frontend_url: str = "http://localhost:3000"

    # ==========================================================================
    # AI Services
    # ==========================================================================

    groq_api_key: str | None = None
    openai_api_key: str | None = None
    langsmith_api_key: str | None = None

    # ==========================================================================
    # AWS (Future)
    # ==========================================================================

    aws_region: str | None = None
    s3_bucket_name: str | None = None

    # ==========================================================================
    # Security
    # ==========================================================================

    secret_key: str = Field(...)
    access_token_expire_minutes: int = 30


settings = Settings()
