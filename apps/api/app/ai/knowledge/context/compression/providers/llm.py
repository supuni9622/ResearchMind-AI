"""
LLM-backed compression provider (V4).

Asks the Generation Platform to summarize each chunk down to only the
content relevant to the query, one `GenerationService.generate()` call per
chunk -- unlike `LangChainCompressionProvider`, which extracts via a single
`ContextualCompressionRetriever` pass and drops chunks with nothing
relevant, this provider never drops a chunk: every field but `content` is
carried over unchanged, and a chunk whose summarization fails (or comes
back empty) falls back to its original, uncompressed content rather than
being removed.
"""

from __future__ import annotations

import asyncio
from time import perf_counter

import structlog
from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.exceptions import (
    CompressionProviderError,
)
from app.ai.knowledge.context.compression.interfaces import (
    CompressionProvider,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
    CompressionResult,
    CompressionStatistics,
    LLMCompressionConfig,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
    PromptContext,
)
from app.ai.runtime.generation.models import (
    GenerationRequest,
)
from app.ai.runtime.generation.service import (
    GenerationService,
)

logger = structlog.get_logger()

SYSTEM_PROMPT = (
    "You compress a single retrieved context chunk for a RAG pipeline. "
    "Given the user's question and one chunk of context, return a concise "
    "summary containing only the information relevant to answering the "
    "question. Preserve exact facts, numbers, and terminology from the "
    "chunk. Respond with the summary only -- no preamble, no commentary."
)


class LLMCompressionProvider(
    CompressionProvider,
):
    """
    Query-aware, per-chunk compression backed by the Generation Platform.
    """

    def __init__(
        self,
        generation_service: GenerationService | None = None,
        config: LLMCompressionConfig | None = None,
    ) -> None:
        # Injected explicitly (tests, a shared instance) or lazily built
        # from the Generation Platform's composition root on first use --
        # kept lazy, like LangChainCompressionProvider's LLM, so
        # registering this provider never requires constructing a full
        # GenerationService (provider registry, prompt/token-counter
        # services, ...) up front.
        self._generation_service = generation_service

        self._config = config or LLMCompressionConfig()

    async def compress(
        self,
        request: CompressionRequest,
    ) -> CompressionResult:

        chunks = request.chunks

        if not chunks:
            return CompressionResult(
                strategy=CompressionStrategy.LLM,
                chunks=[],
                statistics=CompressionStatistics(),
            )

        query = (request.query or "").strip()

        if not query:
            raise CompressionProviderError(
                "LLMCompressionProvider requires CompressionRequest.query -- "
                "the compression prompt summarizes each chunk relative to it."
            )

        started = perf_counter()

        logger.info(
            "context.compression.llm.started",
            provider="llm",
            strategy=CompressionStrategy.LLM.value,
            documents_before=len(chunks),
        )

        compressed_chunks = list(
            await asyncio.gather(
                *(self._compress_chunk(query, chunk) for chunk in chunks),
            )
        )

        duration_ms = (perf_counter() - started) * 1000

        original_tokens = self._estimate_tokens(chunks)
        compressed_tokens = self._estimate_tokens(compressed_chunks)

        statistics = CompressionStatistics(
            original_chunks=len(chunks),
            compressed_chunks=len(compressed_chunks),
            removed_chunks=0,
            estimated_saved_tokens=max(original_tokens - compressed_tokens, 0),
            original_tokens=original_tokens,
            compressed_tokens=compressed_tokens,
            duration_ms=duration_ms,
        )

        logger.info(
            "context.compression.llm.completed",
            provider="llm",
            strategy=CompressionStrategy.LLM.value,
            documents_before=statistics.original_chunks,
            documents_after=statistics.compressed_chunks,
            tokens_saved=statistics.estimated_saved_tokens,
            duration_ms=duration_ms,
        )

        return CompressionResult(
            strategy=CompressionStrategy.LLM,
            chunks=compressed_chunks,
            statistics=statistics,
        )

    # ==================================================================
    # Internals
    # ==================================================================

    async def _compress_chunk(
        self,
        query: str,
        chunk: ContextChunk,
    ) -> ContextChunk:
        """
        Summarizes a single chunk relative to `query`.

        Never raises -- a chunk this fails for (empty content, provider
        error, empty summary) falls back to being returned unchanged, per
        the PRD's "compression failures should never break generation"
        policy applied at chunk granularity.
        """

        if not chunk.content.strip():
            return chunk

        try:
            result = await self._get_generation_service().generate(
                request=GenerationRequest(
                    prompt_context=self._to_prompt_context(chunk),
                    user_prompt=self._build_user_prompt(query, chunk),
                    system_prompt=SYSTEM_PROMPT,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                ),
                provider=self._config.provider,
            )
        except Exception as exc:
            logger.warning(
                "context.compression.llm.chunk_failed",
                provider="llm",
                chunk_id=str(chunk.chunk_id),
                error_type=type(exc).__name__,
                error=str(exc),
            )

            return chunk

        summary = result.content.strip()

        if not summary:
            return chunk

        return chunk.model_copy(
            update={"content": summary},
        )

    def _get_generation_service(self) -> GenerationService:

        if self._generation_service is None:
            from app.ai.runtime.generation.create import (
                create_generation_service,
            )

            self._generation_service = create_generation_service()

        return self._generation_service

    @staticmethod
    def _to_prompt_context(
        chunk: ContextChunk,
    ) -> PromptContext:

        return PromptContext(
            context=chunk.content,
            chunks=[chunk],
            citations=[],
        )

    @staticmethod
    def _build_user_prompt(
        query: str,
        chunk: ContextChunk,
    ) -> str:

        return f"Question: {query}\n\nContext chunk:\n{chunk.content}"

    @staticmethod
    def _estimate_tokens(
        chunks: list[ContextChunk],
    ) -> int:

        return sum(len(chunk.content) // 4 for chunk in chunks)
