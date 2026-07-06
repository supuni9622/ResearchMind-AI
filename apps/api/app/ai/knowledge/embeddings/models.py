"""
Canonical embedding models for the Knowledge Platform.

Every embedding provider (Sentence Transformers, Voyage AI, OpenAI,
BGE, Instructor, etc.) must produce this representation.

This module defines the framework-independent embedding model consumed by:

- Vector Store Platform
- Retrieval Platform
- Reranking Platform
- Runtime Evaluation
- Experimentation Platform
- Future Agentic AI workflows
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.embeddings.enums import EmbeddingProvider

# ============================================================================
# Vector
# ============================================================================


class EmbeddingVector(BaseModel):
    """
    Numerical vector representing a chunk.
    """

    model_config = ConfigDict(extra="forbid")

    values: list[float] = Field(
        description="Embedding vector values.",
    )

    dimensions: int = Field(
        description="Embedding dimensionality.",
    )


# ============================================================================
# Provenance
# ============================================================================


class EmbeddingProvenance(BaseModel):
    """
    Information describing where this embedding originated.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: UUID = Field(
        description="Source document identifier.",
    )

    chunk_id: UUID = Field(
        description="Source chunk identifier.",
    )

    filename: str = Field(
        description="Original filename.",
    )


# ============================================================================
# Provider Information
# ============================================================================


class EmbeddingProviderMetadata(BaseModel):
    """
    Information describing the provider that generated the embedding.
    """

    model_config = ConfigDict(extra="forbid")

    provider: EmbeddingProvider = Field(
        description="Embedding provider.",
    )

    model: str = Field(
        description="Embedding model.",
    )

    model_version: str | None = Field(
        default=None,
        description="Embedding model version.",
    )


# ============================================================================
# Statistics
# ============================================================================


class EmbeddingStatistics(BaseModel):
    """
    Statistics describing the embedding generation.
    """

    model_config = ConfigDict(extra="forbid")

    character_count: int = 0

    word_count: int = 0

    estimated_token_count: int = 0


# ============================================================================
# Experiment Metadata
# ============================================================================


class EmbeddingExperiment(BaseModel):
    """
    Metadata describing how the embedding was produced.

    These fields support experimentation, benchmarking,
    reproducibility, and future evaluation.
    """

    model_config = ConfigDict(extra="forbid")

    provider: EmbeddingProvider = Field(
        description="Embedding provider used to generate the embedding.",
    )

    provider_version: str = Field(
        default="1.0",
        description="Version of the embedding provider implementation.",
    )

    configuration_fingerprint: str = Field(
        description="Stable fingerprint of the embedding provider configuration.",
    )

    experiment_tag: str | None = Field(
        default=None,
        description="Optional experiment identifier.",
    )

    additional_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific metadata.",
    )


# ============================================================================
# Embedding
# ============================================================================


class Embedding(BaseModel):
    """
    Canonical embedding produced by the Embedding Platform.

    The Embedding is the canonical object flowing through downstream AI
    platforms. Provider SDK objects are never exposed outside providers.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(
        description="Unique embedding identifier.",
    )

    provenance: EmbeddingProvenance

    provider: EmbeddingProviderMetadata

    statistics: EmbeddingStatistics

    experiment: EmbeddingExperiment

    vector: EmbeddingVector
