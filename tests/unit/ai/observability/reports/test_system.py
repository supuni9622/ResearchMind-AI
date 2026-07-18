"""
Unit tests for SystemReportBuilder.

Covers:
- Zero-sample statistics render a minimal report without crashing
- Percentiles/aggregations/rankings render for a populated snapshot
"""

from __future__ import annotations

from app.ai.observability.reports.system import SystemReportBuilder
from app.ai.observability.statistics.enums import TimeWindow
from app.ai.observability.statistics.models import (
    PercentileStats,
    RankingEntry,
    StatisticsSnapshot,
)


async def test_zero_sample_report_does_not_crash() -> None:
    stats = StatisticsSnapshot(window=TimeWindow.HOURLY, sample_count=0)

    report = SystemReportBuilder.build(stats)

    assert "Sample Count: 0" in report
    assert "Percentiles" not in report


async def test_populated_report_includes_percentiles_and_rankings() -> None:
    stats = StatisticsSnapshot(
        window=TimeWindow.DAILY,
        sample_count=10,
        latency_percentiles=PercentileStats(p50=100.0, p90=150.0, p95=180.0, p99=200.0),
        average_latency_ms=110.0,
        average_cost_usd=0.02,
        cache_hit_rate=0.5,
        provider_rankings=[RankingEntry(key="groq", value=6.0, sample_count=6)],
    )

    report = SystemReportBuilder.build(stats)

    assert "p50: 100.00 ms" in report
    assert "Average Latency: 110.00 ms" in report
    assert "Cache Hit Rate: 50.0%" in report
    assert "groq" in report
