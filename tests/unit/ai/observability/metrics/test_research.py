"""
Unit tests for build_research_metrics_snapshot.

Covers:
- research_id/research_duration_ms are read from ResearchOutcome
- every other field defaults to None (no Research Runtime exists yet to
  populate planning/iteration/tool-call data)
"""

from __future__ import annotations

import uuid

from app.ai.observability.metrics.research import build_research_metrics_snapshot
from app.ai.research.models import ResearchOutcome


async def test_research_duration_is_read_from_outcome() -> None:
    outcome = ResearchOutcome(
        research_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        query="what is rag?",
        answer="Retrieval augmented generation.",
        citations=[],
        sources=[],
        duration_ms=250.0,
    )

    snapshot = build_research_metrics_snapshot(outcome)

    assert snapshot.research_id == outcome.research_id
    assert snapshot.research_duration_ms == 250.0


async def test_unimplemented_fields_default_to_none() -> None:
    outcome = ResearchOutcome(
        research_id=uuid.uuid4(),
        conversation_id=uuid.uuid4(),
        query="what is rag?",
        answer="Retrieval augmented generation.",
        citations=[],
        sources=[],
        duration_ms=250.0,
    )

    snapshot = build_research_metrics_snapshot(outcome)

    assert snapshot.planning_duration_ms is None
    assert snapshot.review_duration_ms is None
    assert snapshot.sub_questions is None
    assert snapshot.tool_calls is None
    assert snapshot.mcp_calls is None
    assert snapshot.iterations is None
    assert snapshot.total_cost is None
    assert snapshot.total_tokens is None
