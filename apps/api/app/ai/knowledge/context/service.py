from __future__ import annotations

from time import perf_counter
from uuid import UUID

from app.ai.guardrails.exceptions import GuardrailBlockedError
from app.ai.guardrails.service import GuardrailService
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
from app.ai.knowledge.context.formatter.enums import PromptFormatStrategy
from app.ai.knowledge.context.formatter.service import PromptFormatterService
from app.ai.knowledge.context.guardrails.enums import (
    GuardrailStrategy,
)
from app.ai.knowledge.context.guardrails.service import ContextGuardrailService
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
        guardrail_service: ContextGuardrailService,
        prompt_formatter: PromptFormatterService,
        guardrail_platform_service: GuardrailService | None = None,
    ) -> None:
        self._parent_expansion = parent_expansion_service
        self._dedup = DeduplicationService()

        self._ordering = ContextOrderingService()

        self._compression = compression_service

        self._citations = citation_service
        self._merge = AdjacentMergeService()
        self._guardrails = guardrail_service
        self._formatter = prompt_formatter

        self._guardrail_platform = guardrail_platform_service
        """
        Optional (guardrail_integration_prd.md §8 "Retrieval
        Integration"). Distinct from `self._guardrails`
        (`ContextGuardrailService`), the pre-existing chunk-level
        sanitizer this pipeline already ran -- see `build()`'s "#
        Guardrails" step below, which still runs unconditionally and is
        untouched. This is the platform-level `GuardrailService`'s
        retrieval stage (source trust, citation integrity, access
        control, and that same sanitizer composed as one of four
        checks -- see `guardrails/create.py`), run once up front on the
        raw retrieved set and able to hard-block the whole run, not just
        filter individual risky chunks. `None` skips it entirely.
        """

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

        if self._guardrail_platform is not None:
            await self._enforce_retrieval_guardrails(
                chunks,
            )

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

        # Guardrails
        guardrail_result = await self._guardrails.validate(
            strategy=(GuardrailStrategy.RULE_BASED),
            chunks=chunks,
        )

        chunks = guardrail_result.chunks

        # citation

        citation_result = await self._citations.build(
            chunks,
        )

        prompt_context = PromptContext(
            context="",
            chunks=chunks,
            citations=(citation_result.citations),
        )
        formatting_result = await self._formatter.format(
            strategy=(PromptFormatStrategy.DEFAULT),
            context=(prompt_context),
        )
        prompt_context.context = formatting_result.formatted_context

        duration_ms = (perf_counter() - started) * 1000

        return ContextResult(
            prompt_context=prompt_context,
            statistics=ContextStatistics(
                input_chunks=(len(retrieval.chunks)),
                output_chunks=(len(chunks)),
                compressed_chunks=(
                    embedding_result.statistics.removed_chunks
                    + compression_result.statistics.removed_chunks
                ),
                total_tokens=(sum(len(chunk.content) // 4 for chunk in chunks)),
                duration_ms=(duration_ms),
                suspicious_chunks=(guardrail_result.statistics.suspicious_chunks),
                malicious_chunks=(guardrail_result.statistics.malicious_chunks),
                security_warnings=(guardrail_result.warnings),
            ),
        )

    async def _enforce_retrieval_guardrails(
        self,
        chunks: list[ContextChunk],
    ) -> None:
        """
        guardrail_integration_prd.md §8: "Retrieved Chunks -> evaluate_retrieval()
        -> Context Builder", run on the raw retrieved set before any of
        dedup/expansion/merge/compression touches it. Citations don't
        exist yet at this point (`self._citations.build()` runs later),
        so `citation_integrity`'s check is a no-op here -- consistent
        with `GuardrailService.evaluate_retrieval()`'s own citations=None
        default.
        """

        assert self._guardrail_platform is not None

        retrieval_result = await self._guardrail_platform.evaluate_retrieval(
            chunks,
        )

        if retrieval_result.blocked:
            raise GuardrailBlockedError(
                f"Retrieval blocked by guardrails: "
                f"{'; '.join(issue.message for issue in retrieval_result.issues)}"
            )
