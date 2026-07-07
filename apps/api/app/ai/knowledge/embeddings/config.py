"""
Embedding configuration models.

These configuration models define the behavior of embedding providers.

The Embedding Platform intentionally separates provider configuration
from provider implementation to support experimentation,
reproducibility, and future provider versioning.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BaseEmbeddingConfig(BaseModel):
    """
    Base configuration shared by all embedding providers.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    batch_size: int = Field(
        default=32,
        ge=1,
        description="Maximum number of chunks embedded per batch.",
    )

    normalize_embeddings: bool = Field(
        default=True,
        description="Whether generated vectors should be normalized.",
    )


class SentenceTransformerEmbeddingConfig(BaseEmbeddingConfig):
    """
    Configuration for the Sentence Transformers provider.
    """

    batch_size: int = Field(
        default=64,
        ge=1,
        description="Maximum number of chunks embedded per local inference batch.",
    )

    model_name: str = Field(
        default="all-MiniLM-L6-v2",
    )

    device: str = Field(
        default="cpu",
    )

    trust_remote_code: bool = Field(
        default=False,
    )

    show_progress_bar: bool = Field(
        default=False,
    )

    convert_to_numpy: bool = Field(
        default=True,
    )


class VoyageAIEmbeddingConfig(BaseEmbeddingConfig):
    """
    Configuration for the Voyage AI embedding provider.
    """

    batch_size: int = Field(
        default=32,
        ge=1,
        description="Maximum number of chunks embedded per API request.",
    )

    model_name: str = Field(
        default="voyage-3-lite",
    )

    input_type: str = Field(
        default="document",
    )


class OpenAIEmbeddingConfig(BaseEmbeddingConfig):
    """
    Configuration for the OpenAI embedding provider.
    """

    batch_size: int = Field(
        default=128,
        ge=1,
        description="Maximum number of chunks embedded per API request.",
    )

    model_name: str = Field(
        default="text-embedding-3-small",
    )
