from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """AI Core configuration."""

    model_config = SettingsConfigDict(
        env_prefix="AI_",
        extra="ignore",
    )

    aws_region: str = Field(default="us-east-1")

    s3_bucket_name: str

    s3_endpoint_url: str | None = None
