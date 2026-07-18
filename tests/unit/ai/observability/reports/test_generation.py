"""
Unit tests for GenerationReportBuilder.

Covers:
- Report includes core identifiers, latency, tokens, and cost figures
- Optional validation/guardrail scores render "n/a" when unset
"""

from __future__ import annotations

from uuid import uuid4

from app.ai.observability.reports.generation import GenerationReportBuilder
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.observability.models import GenerationMetricsSnapshot


def _snapshot(**overrides: object) -> GenerationMetricsSnapshot:
    defaults: dict[str, object] = dict(
        request_id=uuid4(),
        generation_id=uuid4(),
        provider=GenerationProvider.GROQ,
        model="test-model",
        latency_ms=123.456,
        retries=0,
        regeneration_count=0,
        cache_hit=False,
        prompt_tokens=10,
        completion_tokens=20,
        total_tokens=30,
        estimated_cost_usd=0.001234,
        guardrail_blocked=False,
    )
    defaults.update(overrides)
    return GenerationMetricsSnapshot(**defaults)


async def test_report_includes_core_fields() -> None:
    snapshot = _snapshot()

    report = GenerationReportBuilder.build(snapshot)

    assert str(snapshot.generation_id) in report
    assert "groq" in report
    assert "test-model" in report
    assert "123.46 ms" in report
    assert "Total Tokens: 30" in report


async def test_report_shows_na_for_unset_validation_and_guardrail_scores() -> None:
    snapshot = _snapshot()

    report = GenerationReportBuilder.build(snapshot)

    assert "Validation Score: n/a" in report
    assert "Hallucination Score: n/a" in report
    assert "Risk Score: n/a" in report


async def test_report_includes_cumulative_session_cost_when_present() -> None:
    snapshot = _snapshot(cumulative_session_cost_usd=1.5)

    report = GenerationReportBuilder.build(snapshot)

    assert "Cumulative Session Cost" in report
