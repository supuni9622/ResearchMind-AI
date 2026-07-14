"""
Unit tests for DeduplicationService.

Covers:
- Duplicate chunk_ids are collapsed, keeping the first occurrence
- Order of first occurrence is preserved
- No duplicates leaves the list unchanged
- Empty input does not raise
"""

from __future__ import annotations

import uuid

from app.ai.knowledge.context.builders.deduplication import DeduplicationService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


def test_deduplicate_collapses_repeated_chunk_ids() -> None:
    chunk_id = uuid.uuid4()
    first = make_context_chunk(chunk_id=chunk_id, content="first copy")
    duplicate = make_context_chunk(chunk_id=chunk_id, content="second copy")

    result = DeduplicationService().deduplicate([first, duplicate])

    assert result == [first]
    assert result[0].content == "first copy"


def test_deduplicate_preserves_first_occurrence_order() -> None:
    a = make_context_chunk()
    b = make_context_chunk()
    c = make_context_chunk()

    result = DeduplicationService().deduplicate([b, a, b, c, a])

    assert result == [b, a, c]


def test_deduplicate_with_no_duplicates_is_unchanged() -> None:
    chunks = [make_context_chunk() for _ in range(3)]

    result = DeduplicationService().deduplicate(chunks)

    assert result == chunks


def test_deduplicate_empty_input_returns_empty() -> None:
    assert DeduplicationService().deduplicate([]) == []
