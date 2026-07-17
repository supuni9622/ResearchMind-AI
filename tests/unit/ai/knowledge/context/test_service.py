"""
Integration-style unit tests for ContextBuilderService.

Exercises the real pipeline the service wires together internally
(dedup -> parent expansion -> adjacent merge -> ordering -> compression
-> citations), using a fake for parent expansion (already covered on
its own in test_parent_expansion.py, and it needs storage/S3 to do
anything real), the real composition-root compression service, and the
real CitationService, so this test is the actual end-to-end contract
for the Context Platform's "main scenario": turning a RetrievalResult
into a PromptContext.

The local embedding model backing embedding-redundancy compression is
mocked to always return orthogonal (never-similar) vectors -- this
pipeline stage is unit-tested on its own in
compression/providers/test_embedding.py, and letting it run for real
here would make these tests slow and semantically flaky (two short,
generic test strings can legitimately embed as "similar").

Covers:
- Duplicate chunks are collapsed before anything downstream sees them
- Adjacent chunks from the same document are merged into one block
- Final chunks are ordered by score (post-merge)
- One citation is produced per final chunk, numbered "S1", "S2", ...
- input_chunks reflects the raw retrieval count; output_chunks
  reflects the post-pipeline count
- retrieval_strategy is copied from retrieval.statistics when present,
  and is None when retrieval.statistics is None (no crash)
- parent_chunk_id is parsed out of chunk.metadata into a real UUID
  before being handed to parent expansion
- Compression's removed-chunk count (summed across both the
  embedding-redundancy and token-budget passes) surfaces on
  ContextStatistics.compressed_chunks
- Retrieval Guardrails integration (guardrail_integration_prd.md §8): a
  blocked GuardrailService retrieval result raises before dedup/expansion
  touches the chunks; an allowed result (or no GuardrailService wired at
  all) doesn't change build()'s behavior
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.exceptions import GuardrailBlockedError
from app.ai.guardrails.interfaces import RetrievalGuardrailInterface
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.registry import GuardrailRegistry
from app.ai.guardrails.service import GuardrailService
from app.ai.knowledge.context.citations.service import CitationService
from app.ai.knowledge.context.compression.create import create_compression_service
from app.ai.knowledge.context.compression.enums import CompressionStrategy
from app.ai.knowledge.context.compression.exceptions import CompressionProviderError
from app.ai.knowledge.context.compression.models import CompressionResult, CompressionStatistics
from app.ai.knowledge.context.compression.providers.embedding import EmbeddingCompressionProvider
from app.ai.knowledge.context.compression.providers.token_budget import (
    TokenBudgetCompressionProvider,
)
from app.ai.knowledge.context.compression.registry import CompressionRegistry
from app.ai.knowledge.context.compression.service import CompressionService
from app.ai.knowledge.context.formatter.create import create_prompt_formatter_service
from app.ai.knowledge.context.guardrails.create import create_context_guardrail_service
from app.ai.knowledge.context.models import ContextChunk
from app.ai.knowledge.context.service import ContextBuilderService
from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievalStatistics,
    RetrievedChunk,
)


@pytest.fixture(autouse=True)
def _mock_embedding_model():
    # Distinct one-hot vectors per text -> cosine similarity 0.0 between
    # any two chunks, so embedding-redundancy compression never removes
    # anything in these tests regardless of chunk content.
    model = MagicMock()
    model.encode = MagicMock(side_effect=lambda texts, **kwargs: np.eye(len(texts)))

    with patch(
        "app.ai.knowledge.context.compression.providers.embedding.get_local_embedding_model",
        return_value=model,
    ):
        yield


def _make_chunk(
    *,
    chunk_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    chunk_index: int = 0,
    content: str = "some content",
    score: float = 0.5,
    metadata: dict | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        filename="paper.pdf",
        owner_id="owner-1",
        chunk_index=chunk_index,
        content=content,
        score=score,
        metadata=metadata or {},
    )


def _identity_parent_expansion() -> AsyncMock:
    service = AsyncMock()
    service.expand = AsyncMock(side_effect=lambda chunks: chunks)
    return service


def _make_service(
    *,
    parent_expansion=None,
    guardrail_platform: GuardrailService | None = None,
) -> ContextBuilderService:
    return ContextBuilderService(
        parent_expansion_service=(parent_expansion or _identity_parent_expansion()),
        compression_service=create_compression_service(),
        citation_service=CitationService(),
        guardrail_service=create_context_guardrail_service(),
        prompt_formatter=create_prompt_formatter_service(),
        guardrail_platform_service=guardrail_platform,
    )


def _make_retrieval_result(
    chunks: list[RetrievedChunk],
    *,
    statistics: RetrievalStatistics | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        query=RetrievalQuery(query="what is rag?"),
        execution=RetrievalExecution(),
        statistics=statistics,
        chunks=chunks,
    )


async def test_build_deduplicates_before_anything_downstream() -> None:
    chunk_id = uuid.uuid4()
    duplicate_a = _make_chunk(chunk_id=chunk_id, content="first")
    duplicate_b = _make_chunk(chunk_id=chunk_id, content="second")
    service = _make_service()

    result = await service.build(_make_retrieval_result([duplicate_a, duplicate_b]))

    assert result.statistics.input_chunks == 2
    assert len(result.prompt_context.chunks) == 1


async def test_build_populates_context_with_the_formatted_result() -> None:
    # Regression test: build() used to construct the returned
    # PromptContext from scratch with context="" after formatting,
    # silently discarding the formatter's output instead of returning
    # the prompt_context variable it had just populated.
    chunk = _make_chunk(content="unique payload text")
    service = _make_service()

    result = await service.build(_make_retrieval_result([chunk]))

    assert result.prompt_context.context != ""
    assert "paper.pdf" in result.prompt_context.context
    assert "unique payload text" in result.prompt_context.context


async def test_build_merges_adjacent_chunks_from_the_same_document() -> None:
    document_id = uuid.uuid4()
    first = _make_chunk(document_id=document_id, chunk_index=0, content="alpha", score=0.9)
    second = _make_chunk(document_id=document_id, chunk_index=1, content="beta", score=0.7)
    service = _make_service()

    result = await service.build(_make_retrieval_result([first, second]))

    chunks = result.prompt_context.chunks
    assert len(chunks) == 1
    assert chunks[0].content == "alpha\n\nbeta"


async def test_build_orders_final_chunks_by_score_descending() -> None:
    low = _make_chunk(document_id=uuid.uuid4(), score=0.1, content="low")
    high = _make_chunk(document_id=uuid.uuid4(), score=0.9, content="high")
    service = _make_service()

    result = await service.build(_make_retrieval_result([low, high]))

    scores = [chunk.score for chunk in result.prompt_context.chunks]
    assert scores == sorted(scores, reverse=True)


async def test_build_produces_one_numbered_citation_per_final_chunk() -> None:
    first = _make_chunk(document_id=uuid.uuid4(), content="alpha")
    second = _make_chunk(document_id=uuid.uuid4(), content="beta")
    service = _make_service()

    result = await service.build(_make_retrieval_result([first, second]))

    citation_ids = [citation.citation_id for citation in result.prompt_context.citations]
    assert citation_ids == ["S1", "S2"]


async def test_build_sets_retrieval_strategy_from_statistics() -> None:
    chunk = _make_chunk()
    statistics = RetrievalStatistics(
        provider=RetrievalProvider.QDRANT,
        strategy=RetrievalStrategy.HYBRID,
        duration_ms=1.0,
        returned_chunks=1,
    )
    service = _make_service()

    result = await service.build(_make_retrieval_result([chunk], statistics=statistics))

    assert result.prompt_context.chunks[0].retrieval_strategy == "hybrid"


async def test_build_leaves_retrieval_strategy_none_without_statistics() -> None:
    chunk = _make_chunk()
    service = _make_service()

    result = await service.build(_make_retrieval_result([chunk], statistics=None))

    assert result.prompt_context.chunks[0].retrieval_strategy is None


async def test_build_parses_parent_chunk_id_from_metadata_before_expansion() -> None:
    parent_chunk_id = uuid.uuid4()
    chunk = _make_chunk(metadata={"parent_chunk_id": str(parent_chunk_id)})
    parent_expansion = _identity_parent_expansion()
    service = _make_service(parent_expansion=parent_expansion)

    await service.build(_make_retrieval_result([chunk]))

    forwarded: list[ContextChunk] = parent_expansion.expand.await_args.args[0]
    assert forwarded[0].parent_chunk_id == parent_chunk_id


async def test_build_reports_compressed_chunk_count() -> None:
    # Two large chunks; the real token-budget compressor (max_tokens is
    # hardcoded to 6000 inside ContextBuilderService.build) will drop
    # whichever doesn't fit once one has already been kept.
    huge_a = _make_chunk(document_id=uuid.uuid4(), content="a" * 20_000, score=0.9)
    huge_b = _make_chunk(document_id=uuid.uuid4(), content="b" * 20_000, score=0.1)
    service = _make_service()

    result = await service.build(_make_retrieval_result([huge_a, huge_b]))

    assert result.statistics.compressed_chunks == 1
    assert len(result.prompt_context.chunks) == 1


async def test_build_computes_total_tokens_from_final_chunks() -> None:
    chunk = _make_chunk(content="x" * 40)
    service = _make_service()

    result = await service.build(_make_retrieval_result([chunk]))

    assert result.statistics.total_tokens == 40 // 4


# ==============================================================
# Retrieval Guardrails integration (guardrail_integration_prd.md §8)
# ==============================================================


class _AlwaysBlockRetrievalGuardrail(RetrievalGuardrailInterface):
    @property
    def name(self) -> str:
        return "always_block_retrieval"

    async def check(self, chunks: list[ContextChunk]) -> list[GuardrailIssue]:
        return [
            GuardrailIssue(
                code="blocked",
                severity=GuardrailSeverity.CRITICAL,
                category=GuardrailCategory.ACCESS_CONTROL,
                message="retrieval blocked by test guardrail",
            )
        ]


def _make_guardrail_platform(registry: GuardrailRegistry | None = None) -> GuardrailService:
    return GuardrailService(registry=registry or GuardrailRegistry())


async def test_build_raises_when_retrieval_guardrails_block() -> None:
    registry = GuardrailRegistry()
    registry.register_retrieval_guardrail(_AlwaysBlockRetrievalGuardrail())

    parent_expansion = _identity_parent_expansion()
    service = _make_service(
        parent_expansion=parent_expansion,
        guardrail_platform=_make_guardrail_platform(registry),
    )

    chunk = _make_chunk(content="unique payload text")

    with pytest.raises(GuardrailBlockedError, match="Retrieval blocked"):
        await service.build(_make_retrieval_result([chunk]))

    # Blocked before any of dedup/expansion touches the chunks.
    parent_expansion.expand.assert_not_awaited()


async def test_build_succeeds_when_retrieval_guardrails_allow() -> None:
    service = _make_service(guardrail_platform=_make_guardrail_platform())

    chunk = _make_chunk(content="unique payload text")

    result = await service.build(_make_retrieval_result([chunk]))

    assert len(result.prompt_context.chunks) == 1


async def test_build_skips_retrieval_guardrails_when_none_wired() -> None:
    service = _make_service()

    chunk = _make_chunk(content="unique payload text")

    result = await service.build(_make_retrieval_result([chunk]))

    assert len(result.prompt_context.chunks) == 1


# ==============================================================
# Query-aware compression wiring (context_platform_complexion_prd.md)
# ==============================================================


def _make_service_with_compression(
    compression_service: CompressionService,
) -> ContextBuilderService:
    return ContextBuilderService(
        parent_expansion_service=_identity_parent_expansion(),
        compression_service=compression_service,
        citation_service=CitationService(),
        guardrail_service=create_context_guardrail_service(),
        prompt_formatter=create_prompt_formatter_service(),
    )


def _spy_registry(langchain_provider) -> CompressionRegistry:
    registry = CompressionRegistry()
    registry.register(CompressionStrategy.EMBEDDING_REDUNDANCY, EmbeddingCompressionProvider())
    registry.register(CompressionStrategy.TOKEN_BUDGET, TokenBudgetCompressionProvider())
    registry.register(CompressionStrategy.LANGCHAIN_CONTEXTUAL, langchain_provider)
    return registry


def _passthrough_langchain_provider() -> AsyncMock:
    provider = AsyncMock()
    provider.compress = AsyncMock(
        side_effect=lambda request: CompressionResult(
            strategy=CompressionStrategy.LANGCHAIN_CONTEXTUAL,
            chunks=request.chunks,
            statistics=CompressionStatistics(),
        )
    )
    return provider


async def test_build_passes_query_into_compression_requests() -> None:
    embedding_provider = EmbeddingCompressionProvider()
    token_budget_provider = TokenBudgetCompressionProvider()
    embedding_spy = AsyncMock(side_effect=embedding_provider.compress)
    token_budget_spy = AsyncMock(side_effect=token_budget_provider.compress)
    langchain_provider = _passthrough_langchain_provider()
    registry = CompressionRegistry()
    registry.register(CompressionStrategy.EMBEDDING_REDUNDANCY, MagicMock(compress=embedding_spy))
    registry.register(CompressionStrategy.TOKEN_BUDGET, MagicMock(compress=token_budget_spy))
    registry.register(CompressionStrategy.LANGCHAIN_CONTEXTUAL, langchain_provider)
    service = _make_service_with_compression(CompressionService(registry=registry))

    chunk = _make_chunk(content="unique payload text")

    # Pinned explicitly rather than relying on the global default, since
    # this test only cares about query propagation, not the gate itself
    # (see the dedicated enable_langchain_compression tests below).
    with patch("app.ai.knowledge.context.service.settings") as mock_settings:
        mock_settings.enable_langchain_compression = True

        await service.build(_make_retrieval_result([chunk]), query="what is rag?")

    embedding_call = embedding_spy.await_args
    token_budget_call = token_budget_spy.await_args
    assert embedding_call is not None
    assert token_budget_call is not None
    assert embedding_call.args[0].query == "what is rag?"
    assert langchain_provider.compress.await_args.args[0].query == "what is rag?"
    assert token_budget_call.args[0].query == "what is rag?"


async def test_build_skips_langchain_compression_when_disabled() -> None:
    langchain_provider = _passthrough_langchain_provider()
    service = _make_service_with_compression(
        CompressionService(registry=_spy_registry(langchain_provider))
    )

    chunk = _make_chunk(content="unique payload text")

    with patch("app.ai.knowledge.context.service.settings") as mock_settings:
        mock_settings.enable_langchain_compression = False

        await service.build(_make_retrieval_result([chunk]), query="what is rag?")

    langchain_provider.compress.assert_not_awaited()


async def test_build_skips_langchain_compression_without_a_query_even_when_enabled() -> None:
    langchain_provider = _passthrough_langchain_provider()
    service = _make_service_with_compression(
        CompressionService(registry=_spy_registry(langchain_provider))
    )

    chunk = _make_chunk(content="unique payload text")

    with patch("app.ai.knowledge.context.service.settings") as mock_settings:
        mock_settings.enable_langchain_compression = True

        await service.build(_make_retrieval_result([chunk]))

    langchain_provider.compress.assert_not_awaited()


async def test_build_runs_langchain_compression_when_enabled_with_a_query() -> None:
    langchain_provider = _passthrough_langchain_provider()
    service = _make_service_with_compression(
        CompressionService(registry=_spy_registry(langchain_provider))
    )

    chunk = _make_chunk(content="unique payload text")

    with patch("app.ai.knowledge.context.service.settings") as mock_settings:
        mock_settings.enable_langchain_compression = True

        result = await service.build(_make_retrieval_result([chunk]), query="what is rag?")

    langchain_provider.compress.assert_awaited_once()
    assert langchain_provider.compress.await_args.args[0].query == "what is rag?"
    assert len(result.prompt_context.chunks) == 1


async def test_build_falls_back_when_langchain_compression_fails() -> None:
    langchain_provider = AsyncMock()
    langchain_provider.compress = AsyncMock(side_effect=CompressionProviderError("boom"))
    service = _make_service_with_compression(
        CompressionService(registry=_spy_registry(langchain_provider))
    )

    chunk = _make_chunk(content="unique payload text")

    with patch("app.ai.knowledge.context.service.settings") as mock_settings:
        mock_settings.enable_langchain_compression = True

        result = await service.build(_make_retrieval_result([chunk]), query="what is rag?")

    assert len(result.prompt_context.chunks) == 1
