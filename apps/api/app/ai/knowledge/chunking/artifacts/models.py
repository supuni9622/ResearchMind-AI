"""
Canonical chunk artifact models.

A ChunkArtifact represents a complete chunking execution for a document.

Unlike the Chunk model, which represents a single knowledge unit,
the ChunkArtifact represents an entire chunking run and is the
canonical persistence model written to S3 as:

    chunks.json

The ChunkArtifact is the contract between the Chunking Platform and all
downstream AI platforms including:

- Embedding Platform
- Vector Store
- Retrieval
- Evaluation
- Future Agentic AI workflows
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.ai.knowledge.chunking.enums import ChunkingStrategy
from app.ai.knowledge.chunking.models import Chunk
from pydantic import BaseModel, ConfigDict, Field

# ============================================================================
# Document Information
# ============================================================================


class ChunkArtifactDocument(BaseModel):
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
# Strategy Information
# ============================================================================


class ChunkArtifactStrategy(BaseModel):
    """
    Information describing the chunking strategy.
    """

    model_config = ConfigDict(extra="forbid")

    strategy: ChunkingStrategy = Field(
        description="Chunking strategy used.",
    )

    strategy_version: str = Field(
        description="Chunking provider version.",
    )

    configuration_fingerprint: str = Field(
        description="Fingerprint of the provider configuration.",
    )


# ============================================================================
# Artifact Statistics
# ============================================================================


class ChunkArtifactStatistics(BaseModel):
    """
    Aggregate statistics describing the chunk artifact.
    """

    model_config = ConfigDict(extra="forbid")

    total_chunks: int = 0

    total_characters: int = 0

    total_words: int = 0

    total_estimated_tokens: int = 0

    average_chunk_size: float = 0.0

    average_word_count: float = 0.0

    average_token_count: float = 0.0


# ============================================================================
# Evaluation
# ============================================================================


class ChunkArtifactEvaluation(BaseModel):
    """
    Evaluation metadata.

    These fields are intentionally included now so that future evaluation
    features can populate them without changing the artifact schema.
    """

    model_config = ConfigDict(extra="forbid")

    latency_ms: float | None = None

    notes: str | None = None

    additional_metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


# ============================================================================
# Chunk Artifact
# ============================================================================


class ChunkArtifact(BaseModel):
    """
    Canonical persistence model representing a chunking execution.

    This model is serialized to:

        chunks.json

    and persisted to Amazon S3.
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier of this chunk artifact.",
    )

    version: str = Field(
        default="1.0",
        description="Artifact schema version.",
    )

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the artifact was generated.",
    )

    document: ChunkArtifactDocument

    strategy: ChunkArtifactStrategy

    statistics: ChunkArtifactStatistics

    evaluation: ChunkArtifactEvaluation = Field(
        default_factory=ChunkArtifactEvaluation,
    )

    chunks: list[Chunk] = Field(
        default_factory=list,
        description="Canonical chunks produced by the chunking platform.",
    )
