from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.ai.knowledge.context.builders.adjacent_merge import (
    AdjacentMergeService,
)
from app.ai.knowledge.context.builders.deduplication import (
    DeduplicationService,
)
from app.ai.knowledge.context.builders.ordering import (
    ContextOrderingService,
)
from app.ai.knowledge.context.builders.parent_expansion import (
    ParentExpansionService,
)
from app.ai.knowledge.context.citations.service import (
    CitationService,
)
from app.ai.knowledge.context.compression.enums import (
    CompressionStrategy,
)
from app.ai.knowledge.context.compression.models import (
    CompressionRequest,
)
from app.ai.knowledge.context.compression.service import (
    CompressionService,
)
from app.ai.knowledge.context.interfaces import (
    ContextBuilderInterface,
)
from app.ai.knowledge.context.models import (
    ContextChunk,
    ContextResult,
    ContextStatistics,
    PromptContext,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalResult,
)


class ContextBuilderService(
    ContextBuilderInterface,
):
    def __init__(
        self,
        parent_expansion_service: ParentExpansionService,
        compression_service: CompressionService,
        citation_service: CitationService,
    ) -> None:
        self._parent_expansion = parent_expansion_service
        self._dedup = DeduplicationService()

        self._ordering = ContextOrderingService()

        self._compression = compression_service

        self._citations = citation_service
        self._merge = AdjacentMergeService()

    async def build(
        self,
        retrieval: RetrievalResult,
    ) -> ContextResult:

        started = perf_counter()

        chunks = [
            ContextChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                owner_id=chunk.owner_id,
                chunk_index=chunk.chunk_index,
                content=chunk.content,
                score=chunk.score,
                retrieval_strategy=(
                    retrieval.statistics.strategy.value if retrieval.statistics else None
                ),
                parent_chunk_id=(
                    UUID(chunk.metadata["parent_chunk_id"])
                    if chunk.metadata.get("parent_chunk_id")
                    else None
                ),
                metadata=chunk.metadata,
            )
            for chunk in retrieval.chunks
        ]

        chunks = self._dedup.deduplicate(
            chunks,
        )
        chunks = await self._parent_expansion.expand(
            chunks,
        )
        chunks = self._merge.merge(
            chunks,
        )

        chunks = self._ordering.order(
            chunks,
        )

        embedding_result = await self._compression.compress(
            strategy=(CompressionStrategy.EMBEDDING_REDUNDANCY),
            request=(
                CompressionRequest(
                    chunks=chunks,
                )
            ),
        )

        chunks = embedding_result.chunks

        compression_result = await self._compression.compress(
            strategy=(CompressionStrategy.TOKEN_BUDGET),
            request=(
                CompressionRequest(
                    chunks=chunks,
                    max_tokens=6000,
                )
            ),
        )

        chunks = compression_result.chunks

        citation_result = await self._citations.build(
            chunks,
        )

        duration_ms = (perf_counter() - started) * 1000

        return ContextResult(
            prompt_context=PromptContext(
                context="",
                chunks=chunks,
                citations=(citation_result.citations),
            ),
            statistics=ContextStatistics(
                input_chunks=len(retrieval.chunks),
                output_chunks=len(chunks),
                compressed_chunks=(
                    embedding_result.statistics.removed_chunks
                    + compression_result.statistics.removed_chunks
                ),
                total_tokens=(sum(len(chunk.content) // 4 for chunk in chunks)),
                duration_ms=duration_ms,
            ),
        )
