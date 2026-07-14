from __future__ import annotations

from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)
from pydantic import BaseModel, ConfigDict


class CompressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[ContextChunk]

    query: str | None = None

    top_k: int | None = None

    max_tokens: int | None = None


class CompressionStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_chunks: int = 0

    compressed_chunks: int = 0

    removed_chunks: int = 0

    estimated_saved_tokens: int = 0


class CompressionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: CompressionStrategy

    chunks: list[ContextChunk]

    statistics: CompressionStatistics
