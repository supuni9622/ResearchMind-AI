"""
Unit tests for AdjacentMergeService.

Covers:
- Two adjacent chunks from the same document merge into one block
- Three (or more) consecutive chunks merge into a single block --
  regression test for a bug where the adjacency check compared against
  the block's pinned starting index (chunk_index is set to `min()` on
  every merge) instead of the last-absorbed index, so a chain longer
  than two chunks silently broke after the first merge
- A gap in chunk_index prevents merging
- Chunks from different documents never merge, even with adjacent
  chunk_index values
- Merging concatenates content, keeps the max score, keeps the min
  (starting) chunk_index, and records every absorbed chunk_id
- Input order doesn't matter -- the service sorts internally
- Single-chunk and empty input are handled without raising
"""

from __future__ import annotations

import uuid

from app.ai.knowledge.context.builders.adjacent_merge import AdjacentMergeService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


def test_merge_empty_input_returns_empty() -> None:
    assert AdjacentMergeService().merge([]) == []


def test_merge_single_chunk_is_unchanged_but_gains_merged_ids() -> None:
    chunk = make_context_chunk(chunk_index=0)

    result = AdjacentMergeService().merge([chunk])

    assert len(result) == 1
    assert result[0].content == chunk.content
    assert result[0].merged_chunk_ids == [chunk.chunk_id]


def test_merge_combines_two_adjacent_chunks_from_the_same_document() -> None:
    document_id = uuid.uuid4()
    first = make_context_chunk(
        document_id=document_id, chunk_index=5, content="chunk five", score=0.4
    )
    second = make_context_chunk(
        document_id=document_id, chunk_index=6, content="chunk six", score=0.7
    )

    result = AdjacentMergeService().merge([first, second])

    assert len(result) == 1
    merged = result[0]
    assert merged.content == "chunk five\n\nchunk six"
    assert merged.chunk_index == 5
    assert merged.score == 0.7
    assert merged.merged_chunk_ids == [first.chunk_id, second.chunk_id]


def test_merge_chains_three_consecutive_chunks_into_one_block() -> None:
    # Regression test: chunk_index gets pinned to the block's minimum
    # on every merge, so adjacency must be checked against the last
    # absorbed index, not against current.chunk_index directly.
    document_id = uuid.uuid4()
    chunks = [
        make_context_chunk(document_id=document_id, chunk_index=15, content="c15"),
        make_context_chunk(document_id=document_id, chunk_index=16, content="c16"),
        make_context_chunk(document_id=document_id, chunk_index=17, content="c17"),
    ]

    result = AdjacentMergeService().merge(chunks)

    assert len(result) == 1
    merged = result[0]
    assert merged.content == "c15\n\nc16\n\nc17"
    assert merged.chunk_index == 15
    assert merged.merged_chunk_ids == [chunk.chunk_id for chunk in chunks]


def test_merge_does_not_bridge_a_gap_in_chunk_index() -> None:
    document_id = uuid.uuid4()
    first = make_context_chunk(document_id=document_id, chunk_index=1)
    third = make_context_chunk(document_id=document_id, chunk_index=3)

    result = AdjacentMergeService().merge([first, third])

    assert len(result) == 2
    assert result[0].merged_chunk_ids == [first.chunk_id]
    assert result[1].merged_chunk_ids == [third.chunk_id]


def test_merge_never_combines_chunks_from_different_documents() -> None:
    # Same numeric chunk_index adjacency, but different source documents.
    first = make_context_chunk(document_id=uuid.uuid4(), chunk_index=0)
    second = make_context_chunk(document_id=uuid.uuid4(), chunk_index=1)

    result = AdjacentMergeService().merge([first, second])

    assert len(result) == 2


def test_merge_is_order_independent() -> None:
    document_id = uuid.uuid4()
    first = make_context_chunk(document_id=document_id, chunk_index=0, content="a")
    second = make_context_chunk(document_id=document_id, chunk_index=1, content="b")

    # Pass them in reverse; the service sorts by (document_id, chunk_index)
    # internally before merging.
    result = AdjacentMergeService().merge([second, first])

    assert len(result) == 1
    assert result[0].content == "a\n\nb"
