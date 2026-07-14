from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.ai.knowledge.context.citations.models import (
    Citation,
)
from pydantic import BaseModel, ConfigDict, Field


class ContextChunk(BaseModel):
    """
    Canonical context unit.

    Produced from retrieval results and progressively enriched.
    """

    model_config = ConfigDict(extra="forbid")

    chunk_id: UUID

    document_id: UUID

    filename: str

    owner_id: str

    chunk_index: int

    content: str

    score: float

    #
    # Future retrieval metadata
    #

    retrieval_strategy: str | None = None

    #
    # Parent context expansion
    #

    parent_chunk_id: UUID | None = None

    parent_content: str | None = None

    #
    # Citation metadata
    #

    page_numbers: list[int] = Field(
        default_factory=list,
    )

    heading: str | None = None

    heading_path: list[str] = Field(
        default_factory=list,
    )

    citation_id: str | None = None
    merged_chunk_ids: list[UUID] = Field(
        default_factory=list,
    )

    metadata: dict[str, object] = Field(
        default_factory=dict,
    )


class PromptContext(BaseModel):
    """
    Final prompt context sent to the LLM.
    """

    model_config = ConfigDict(extra="forbid")

    context: str

    chunks: list[ContextChunk]
    citations: list[Citation] = Field(
        default_factory=list,
    )


class ContextStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_chunks: int = 0

    output_chunks: int = 0

    compressed_chunks: int = 0

    total_tokens: int = 0

    duration_ms: float = 0


class ContextResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
    )

    prompt_context: PromptContext

    statistics: ContextStatistics
