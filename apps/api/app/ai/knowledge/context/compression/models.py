from __future__ import annotations

from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from pydantic import BaseModel, ConfigDict


class LLMCompressionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: GenerationProvider = GenerationProvider.GROQ

    max_tokens: int = 300

    temperature: float = 0.0


class CompressionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[ContextChunk]

    query: str | None = None

    top_k: int | None = None

    max_tokens: int | None = None
    similarity_threshold: float | None = None


class CompressionStatistics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    original_chunks: int = 0

    compressed_chunks: int = 0

    removed_chunks: int = 0

    estimated_saved_tokens: int = 0

    #
    # Populated by providers that measure token counts and timing
    # (e.g. LangChainCompressionProvider). Left at their defaults by
    # providers that don't -- existing callers only rely on the chunk
    # counts above.
    #

    original_tokens: int = 0

    compressed_tokens: int = 0

    duration_ms: float = 0.0


class CompressionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: CompressionStrategy

    chunks: list[ContextChunk]

    statistics: CompressionStatistics
