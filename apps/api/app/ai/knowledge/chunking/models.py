"""
Canonical chunk models for the Knowledge Platform.

Every chunking provider (Fixed, Recursive, Markdown, Hierarchical,
Semantic, LLM, etc.) must produce this representation.

This module defines the framework-independent chunk model consumed by:

- Embedding Platform
- Vector Store
- Retrieval
- Reranking
- Context Builder
- Citation Engine
- Evaluation
- Future Agentic AI workflows
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.chunking.enums import (
    ChunkContentType,
    ChunkingStrategy,
)

# ============================================================================
# Content
# ============================================================================


class ChunkContent(BaseModel):
    """
    Human-readable content contained in a chunk.
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(
        description="Plain text representation of the chunk.",
    )

    markdown: str | None = Field(
        default=None,
        description="Optional Markdown representation of the chunk.",
    )

    content_type: ChunkContentType = Field(
        default=ChunkContentType.TEXT,
        description="Logical content type represented by the chunk.",
    )


# ============================================================================
# Structure
# ============================================================================


class ChunkStructure(BaseModel):
    """
    Structural information describing where the chunk originated
    within the source document.
    """

    model_config = ConfigDict(extra="forbid")

    heading: str | None = Field(
        default=None,
        description="Nearest heading associated with the chunk.",
    )

    heading_path: list[str] = Field(
        default_factory=list,
        description="Heading hierarchy from the document root.",
    )

    page_numbers: list[int] = Field(
        default_factory=list,
        description="Pages covered by the chunk.",
    )

    hierarchy_level: int | None = Field(
        default=None,
        description="Hierarchy level within the document.",
    )

    parent_chunk_id: UUID | None = Field(
        default=None,
        description="Parent chunk identifier used by hierarchical chunking.",
    )


# ============================================================================
# Statistics
# ============================================================================


class ChunkStatistics(BaseModel):
    """
    Statistics describing a chunk.
    """

    model_config = ConfigDict(extra="forbid")

    character_count: int = 0

    word_count: int = 0

    sentence_count: int = 0

    estimated_token_count: int = 0

    average_token_length: float = 0.0


# ============================================================================
# Provenance
# ============================================================================


class ChunkProvenance(BaseModel):
    """
    Information describing where the chunk originated.
    """

    model_config = ConfigDict(extra="forbid")

    document_id: UUID = Field(
        description="Unique identifier of the source document.",
    )

    filename: str = Field(
        description="Original filename of the source document.",
    )

    parser: str = Field(
        description="Parser implementation used to produce the processed document.",
    )

    parser_version: str | None = Field(
        default=None,
        description="Parser implementation version.",
    )


# ============================================================================
# Experiment Metadata
# ============================================================================


class ChunkExperiment(BaseModel):
    """
    Metadata describing how the chunk was produced.

    These fields support experimentation, benchmarking,
    reproducibility, and future evaluation.
    """

    model_config = ConfigDict(extra="forbid")

    strategy: ChunkingStrategy = Field(
        description="Chunking strategy used to generate this chunk.",
    )

    strategy_version: str = Field(
        default="1.0",
        description="Version of the chunking strategy implementation.",
    )

    configuration_fingerprint: str = Field(
        description="Stable fingerprint of the chunking configuration.",
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
# Chunk
# ============================================================================


class Chunk(BaseModel):
    """
    Canonical knowledge unit of the Knowledge Platform.

    The Chunk is the canonical object that flows through the entire AI
    pipeline. Downstream platforms progressively enrich the same Chunk
    instance rather than replacing it with framework-specific models.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(
        description="Unique chunk identifier.",
    )

    index: int = Field(
        description="Zero-based chunk index within the document.",
    )

    total_chunks: int = Field(
        description="Total number of chunks generated for the document.",
    )

    content: ChunkContent

    structure: ChunkStructure

    statistics: ChunkStatistics

    provenance: ChunkProvenance

    experiment: ChunkExperiment
