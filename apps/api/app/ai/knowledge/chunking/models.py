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
        description="Logical content type represented by this chunk.",
    )


# ============================================================================
# Structure
# ============================================================================


class ChunkStructure(BaseModel):
    """
    Structural information describing where the chunk originated.
    """

    model_config = ConfigDict(extra="forbid")

    heading: str | None = Field(
        default=None,
        description="Nearest heading associated with this chunk.",
    )

    heading_path: list[str] = Field(
        default_factory=list,
        description="Hierarchy of headings from root to current section.",
    )

    page_numbers: list[int] = Field(
        default_factory=list,
        description="Pages covered by this chunk.",
    )

    hierarchy_level: int | None = Field(
        default=None,
        description="Hierarchy level of the chunk within the document.",
    )

    parent_chunk_id: str | None = Field(
        default=None,
        description="Parent chunk identifier for hierarchical chunking.",
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

    filename: str | None = Field(
        default=None,
        description="Original document filename.",
    )

    parser: str = Field(
        description="Parser used to generate the processed document.",
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
    and reproducibility.
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
        description="Unique fingerprint representing the chunking configuration.",
    )

    experiment_tag: str | None = Field(
        default=None,
        description="Optional experiment identifier.",
    )

    additional_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific metadata.",
    )


# ============================================================================
# Chunk
# ============================================================================


class Chunk(BaseModel):
    """
    Canonical knowledge unit of the Knowledge Platform.

    Every downstream AI platform progressively enriches the same Chunk
    instance throughout its lifecycle.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
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
