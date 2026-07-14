"""
Canonical reranking models.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.ai.knowledge.retrieval.models import (
    RetrievedChunk,
)


class RerankingRequest(BaseModel):
    """
    Canonical reranking request.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    query: str

    chunks: list[RetrievedChunk]

    top_k: int = Field(
        default=5,
        ge=1,
    )


class RerankedChunk(BaseModel):
    """
    Chunk with rerank score.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    chunk: RetrievedChunk

    rerank_score: float


class RerankingResult(BaseModel):
    """
    Canonical reranking result.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    chunks: list[RerankedChunk]

    duration_ms: float
