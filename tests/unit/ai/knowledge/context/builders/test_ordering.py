"""
Unit tests for ContextOrderingService.

Covers:
- Chunks are ordered by score, highest first
- Equal scores are broken by ascending chunk_index (lower index first)
- Empty input does not raise
"""

from __future__ import annotations

from app.ai.knowledge.context.builders.ordering import ContextOrderingService

from tests.unit.ai.knowledge.context.factories import make_context_chunk


def test_order_sorts_by_score_descending() -> None:
    low = make_context_chunk(score=0.2)
    high = make_context_chunk(score=0.9)
    mid = make_context_chunk(score=0.5)

    result = ContextOrderingService().order([low, high, mid])

    assert result == [high, mid, low]


def test_order_breaks_ties_by_ascending_chunk_index() -> None:
    later = make_context_chunk(score=0.5, chunk_index=5)
    earlier = make_context_chunk(score=0.5, chunk_index=1)

    result = ContextOrderingService().order([later, earlier])

    assert result == [earlier, later]


def test_order_empty_input_returns_empty() -> None:
    assert ContextOrderingService().order([]) == []
