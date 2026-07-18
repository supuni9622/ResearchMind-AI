"""
Canonical Retrieval Platform models.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.retrieval.enums import (
    RetrievalOperation,
    RetrievalProvider,
    RetrievalStrategy,
)

# ============================================================================
# Query
# ============================================================================


class RetrievalQuery(BaseModel):
    """
    Canonical retrieval query.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=1,
        description="User search query.",
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results.",
    )

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata filters.",
    )


# ============================================================================
# Retrieved Chunk
# ============================================================================


class RetrievedChunk(BaseModel):
    """
    Retrieved knowledge chunk.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: UUID

    document_id: UUID

    filename: str

    owner_id: str

    chunk_index: int

    content: str

    score: float

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


# ============================================================================
# Statistics
# ============================================================================


class RetrievalStatistics(BaseModel):
    """
    Statistics describing a retrieval execution.
    """

    model_config = ConfigDict(extra="forbid")

    provider: RetrievalProvider

    strategy: RetrievalStrategy

    duration_ms: float = Field(
        ge=0,
    )

    returned_chunks: int = Field(
        ge=0,
    )

    #
    # Per-stage breakdown (Observability Platform §5.2). Only populated by
    # `search_hybrid()`, which is the only path that actually runs dense +
    # sparse + optional rerank as distinct sub-stages -- `search()`/
    # `search_sparse()` leave these `None` since `duration_ms` above
    # already *is* their one stage's latency.
    #

    dense_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    sparse_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    metadata_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    rerank_latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    reranker_provider: str | None = None


# ============================================================================
# Execution
# ============================================================================


class RetrievalExecution(BaseModel):
    """
    Retrieval execution metadata.
    """

    model_config = ConfigDict(extra="forbid")

    operation: RetrievalOperation = Field(
        default=RetrievalOperation.SEARCH,
    )

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    completed_at: datetime | None = None


# ============================================================================
# Result
# ============================================================================


class RetrievalResult(BaseModel):
    """
    Canonical retrieval result.
    """

    model_config = ConfigDict(extra="forbid")

    retrieval_id: UUID = Field(
        default_factory=uuid4,
    )

    query: RetrievalQuery

    execution: RetrievalExecution

    statistics: RetrievalStatistics | None = None

    chunks: list[RetrievedChunk] = Field(
        default_factory=list,
    )
