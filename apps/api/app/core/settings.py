#Contains configuration values.

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Environment-specific configuration.

    Values are loaded from the .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Environment
    # ==========================================================================

    environment: str = Field(default="development")

    debug: bool = True

    # ==========================================================================
    # Database
    # ==========================================================================

    database_url: str

    valkey_url: str

    qdrant_url: str

    # ==========================================================================
    # Frontend
    # ==========================================================================

    frontend_url: str = "http://localhost:3000"

    # ==========================================================================
    # AI Services (Future)
    # ==========================================================================

    groq_api_key: str | None = None

    openai_api_key: str | None = None

    langsmith_api_key: str | None = None

    # ==========================================================================
    # AWS (Future)
    # ==========================================================================

    aws_region: str | None = None

    s3_bucket_name: str | None = None


settings = Settings()