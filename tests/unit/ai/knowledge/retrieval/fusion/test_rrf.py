"""
Unit tests for ReciprocalRankFusion.

Covers:
- Fusing dense + sparse only (metadata omitted) still works exactly as
  before -- metadata is purely additive
- A metadata result contributes RRF score to a chunk it shares with
  dense/sparse, boosting its rank
- A metadata-only chunk (not present in dense or sparse) is still
  included in the fused result
- top_k truncates the fused, sorted result
"""

from __future__ import annotations

import uuid

from app.ai.knowledge.retrieval.fusion.rrf import ReciprocalRankFusion
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
)


def _make_chunk(chunk_id: uuid.UUID | None = None) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=uuid.uuid4(),
        filename="test.pdf",
        owner_id="owner-1",
        chunk_index=0,
        content="some chunk text",
        score=0.9,
    )


def _make_result(chunks: list[RetrievedChunk]) -> RetrievalResult:
    return RetrievalResult(
        query=RetrievalQuery(query="rag"),
        execution=RetrievalExecution(),
        chunks=chunks,
    )


async def test_fuse_without_metadata_matches_dense_and_sparse_only() -> None:
    dense_chunk = _make_chunk()
    sparse_chunk = _make_chunk()
    fusion = ReciprocalRankFusion()

    result = await fusion.fuse(
        dense=_make_result([dense_chunk]),
        sparse=_make_result([sparse_chunk]),
        top_k=10,
    )

    assert {chunk.chunk_id for chunk in result.chunks} == {
        dense_chunk.chunk_id,
        sparse_chunk.chunk_id,
    }


async def test_fuse_boosts_a_chunk_present_in_all_three_sources() -> None:
    shared_chunk = _make_chunk()
    dense_only = _make_chunk()
    sparse_only = _make_chunk()
    fusion = ReciprocalRankFusion()

    result = await fusion.fuse(
        dense=_make_result([shared_chunk, dense_only]),
        sparse=_make_result([shared_chunk, sparse_only]),
        metadata=_make_result([shared_chunk]),
        top_k=10,
    )

    # Present in all three retrievers -> highest RRF score -> ranked first.
    assert result.chunks[0].chunk_id == shared_chunk.chunk_id
    assert {chunk.chunk_id for chunk in result.chunks} == {
        shared_chunk.chunk_id,
        dense_only.chunk_id,
        sparse_only.chunk_id,
    }


async def test_fuse_includes_a_metadata_only_chunk() -> None:
    metadata_only_chunk = _make_chunk()
    dense_chunk = _make_chunk()
    fusion = ReciprocalRankFusion()

    result = await fusion.fuse(
        dense=_make_result([dense_chunk]),
        sparse=_make_result([]),
        metadata=_make_result([metadata_only_chunk]),
        top_k=10,
    )

    assert {chunk.chunk_id for chunk in result.chunks} == {
        dense_chunk.chunk_id,
        metadata_only_chunk.chunk_id,
    }


async def test_fuse_respects_top_k() -> None:
    chunks = [_make_chunk() for _ in range(5)]
    fusion = ReciprocalRankFusion()

    result = await fusion.fuse(
        dense=_make_result(chunks),
        sparse=_make_result([]),
        metadata=_make_result([]),
        top_k=2,
    )

    assert len(result.chunks) == 2
