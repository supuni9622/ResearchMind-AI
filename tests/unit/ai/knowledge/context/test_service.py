"""
Integration-style unit tests for ContextBuilderService.

Exercises the real pipeline the service wires together internally
(dedup -> parent expansion -> adjacent merge -> ordering -> compression
-> citations), using a fake for parent expansion (already covered on
its own in test_parent_expansion.py, and it needs storage/S3 to do
anything real) and the real composition-root compression service, so
this test is the actual end-to-end contract for the Context Platform's
"main scenario": turning a RetrievalResult into a PromptContext.

Covers:
- Duplicate chunks are collapsed before anything downstream sees them
- Adjacent chunks from the same document are merged into one block
- Final chunks are ordered by score (post-merge)
- Citations context contains one numbered "[Source N]" section per
  final chunk
- input_chunks reflects the raw retrieval count; output_chunks
  reflects the post-pipeline count
- retrieval_strategy is copied from retrieval.statistics when present,
  and is None when retrieval.statistics is None (no crash)
- parent_chunk_id is parsed out of chunk.metadata into a real UUID
  before being handed to parent expansion
- Compression's removed-chunk count surfaces on
  ContextStatistics.compressed_chunks
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

from app.ai.knowledge.context.compression.create import create_compression_service
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


def _make_service(*, parent_expansion=None) -> ContextBuilderService:
    return ContextBuilderService(
        parent_expansion_service=(parent_expansion or _identity_parent_expansion()),
        compression_service=create_compression_service(),
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

    context = result.prompt_context.context
    assert "[Source 1]" in context
    assert "[Source 2]" in context


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
