"""
Canonical embedding artifact models.

An EmbeddingArtifact represents a complete embedding execution for a
chunk artifact.

Unlike the Embedding model, which represents a single embedded chunk,
the EmbeddingArtifact represents an entire embedding run and is the
canonical persistence model written to S3 as:

    embeddings.json

The EmbeddingArtifact is the contract between the Embedding Platform and
all downstream AI platforms including:

- Vector Store Platform
- Retrieval Platform
- Evaluation Platform
- Experimentation Platform
- Future Agentic AI workflows
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.embeddings.enums import EmbeddingProvider
from app.ai.knowledge.embeddings.models import Embedding
from app.ai.knowledge.vectorstores.enums import VectorDistanceMetric
from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Document Information
# ============================================================================


class EmbeddingArtifactDocument(BaseModel):
    """
    Information about the source document.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: UUID = Field(
        description="Unique identifier of the source document.",
    )

    filename: str = Field(
        description="Original filename.",
    )

    parser: str = Field(
        description="Parser used to produce the processed document.",
    )

    parser_version: str | None = Field(
        default=None,
        description="Parser implementation version.",
    )


# ============================================================================
# Chunking Information
# ============================================================================


class EmbeddingArtifactChunking(BaseModel):
    """
    Information describing the chunking execution that produced the
    source chunks.
    """

    model_config = ConfigDict(extra="forbid")

    strategy: ChunkingStrategy = Field(
        description="Chunking strategy used.",
    )

    strategy_version: str = Field(
        description="Chunking provider version.",
    )

    configuration_fingerprint: str = Field(
        description="Fingerprint of the chunking configuration.",
    )


# ============================================================================
# Embedding Execution
# ============================================================================


class EmbeddingArtifactExecution(BaseModel):
    """
    Information describing the embedding execution.
    """

    model_config = ConfigDict(extra="forbid")

    provider: EmbeddingProvider = Field(
        description="Embedding provider used.",
    )

    provider_version: str = Field(
        description="Embedding provider implementation version.",
    )

    model: str = Field(
        description="Embedding model.",
    )

    model_version: str | None = Field(
        default=None,
        description="Embedding model version.",
    )

    recommended_distance_metric: VectorDistanceMetric = Field(
        description="Distance metric recommended by the embedding provider.",
    )

    configuration_fingerprint: str = Field(
        description="Fingerprint of the embedding configuration.",
    )


# ============================================================================
# Artifact Statistics
# ============================================================================


class EmbeddingArtifactStatistics(BaseModel):
    """
    Aggregate statistics describing the embedding artifact.
    """

    model_config = ConfigDict(extra="forbid")

    total_embeddings: int = 0

    dimensions: int = 0

    total_characters: int = 0

    total_words: int = 0

    total_estimated_tokens: int = 0

    average_dimensions: float = 0.0


# ============================================================================
# Evaluation
# ============================================================================


class EmbeddingArtifactEvaluation(BaseModel):
    """
    Evaluation metadata.

    These fields are intentionally included now so that future runtime
    evaluation features can populate them without changing the artifact
    schema.
    """

    model_config = ConfigDict(extra="forbid")

    latency_ms: float | None = None

    estimated_cost: float | None = None

    notes: str | None = None

    additional_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


# ============================================================================
# Embedding Artifact
# ============================================================================


class EmbeddingArtifact(BaseModel):
    """
    Canonical persistence model representing an embedding execution.

    This model is serialized to:

        embeddings.json

    and persisted to Amazon S3.
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier of this embedding artifact.",
    )

    version: str = Field(
        default="1.0",
        description="Artifact schema version.",
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the artifact was generated.",
    )

    document: EmbeddingArtifactDocument

    chunking: EmbeddingArtifactChunking

    execution: EmbeddingArtifactExecution = Field(
        description="Embedding execution metadata.",
    )

    statistics: EmbeddingArtifactStatistics

    evaluation: EmbeddingArtifactEvaluation = Field(
        default_factory=EmbeddingArtifactEvaluation,
    )

    embeddings: list[Embedding] = Field(
        default_factory=list,
        description="Canonical embeddings produced by the Embedding Platform.",
    )
