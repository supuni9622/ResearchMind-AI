"""
Retrieval Platform configuration models.

These configuration models define the behaviour of retrieval providers.

The Retrieval Platform intentionally separates provider configuration
from provider implementation to support reproducibility,
experimentation, benchmarking, and future provider versioning.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.retrieval.enums import (
    RetrievalStrategy,
)


class BaseRetrievalConfig(BaseModel):
    """
    Base configuration shared by all retrieval providers.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    default_top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Default number of chunks returned.",
    )

    max_top_k: int = Field(
        default=50,
        ge=1,
        description="Maximum supported top-k value.",
    )

    strategy: RetrievalStrategy = Field(
        default=RetrievalStrategy.DENSE,
        description="Retrieval strategy.",
    )

    enable_runtime_metrics: bool = Field(
        default=True,
        description="Collect retrieval runtime metrics.",
    )


class QdrantRetrievalConfig(BaseRetrievalConfig):
    """
    Configuration for Qdrant retrieval.
    """

    collection_name: str = Field(
        default="researchmind_knowledge",
        description="Target Qdrant collection.",
    )

    score_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional minimum similarity score.",
    )

    with_payload: bool = Field(
        default=True,
        description="Return payload metadata.",
    )

    with_vectors: bool = Field(
        default=False,
        description="Return vectors in responses.",
    )

    search_batch_size: int = Field(
        default=100,
        ge=1,
        description="Maximum search batch size.",
    )
