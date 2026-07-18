"""
Unit tests for RetrievalReportBuilder.

Covers:
- Report includes provider/strategy/volume figures
- Unset optional fields render "n/a" instead of crashing on None
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.knowledge.retrieval.enums import RetrievalProvider, RetrievalStrategy
from app.ai.observability.metrics.retrieval import RetrievalMetricsSnapshot
from app.ai.observability.reports.retrieval import RetrievalReportBuilder


async def test_report_includes_provider_strategy_and_volume() -> None:
    snapshot = RetrievalMetricsSnapshot(
        retrieval_id=uuid4(),
        provider=RetrievalProvider.QDRANT,
        strategy=RetrievalStrategy.HYBRID,
        retrieved_chunks=8,
        dense_latency_ms=10.0,
        sparse_latency_ms=5.0,
    )

    report = RetrievalReportBuilder.build(snapshot)

    assert "qdrant" in report
    assert "hybrid" in report
    assert "Retrieved Chunks: 8" in report
    assert "10.00 ms" in report


async def test_report_renders_na_for_unset_optional_fields() -> None:
    snapshot = RetrievalMetricsSnapshot(retrieval_id=uuid4(), retrieved_chunks=0)

    report = RetrievalReportBuilder.build(snapshot)

    assert "Provider: n/a" in report
    assert "Strategy: n/a" in report
    assert "Expanded Chunks: n/a" in report
    assert "Citations: n/a" in report
