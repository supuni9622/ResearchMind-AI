from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.research.charts.models import (
    ChartDataPoint,
    ChartGenerationDecision,
    ChartSpec,
)
from app.ai.runtime.research.charts.necessity import ChartGenerationService
from app.ai.runtime.research.synthesis.models import ResearchDraft, ResearchDraftSection
from app.core.settings import settings


def _draft(**overrides: object) -> ResearchDraft:
    kwargs: dict[str, object] = {
        "title": "Title",
        "abstract": "Abstract",
        "methodology": "Methodology",
        "findings": [
            ResearchDraftSection(heading="Findings", content="Some content.", citation_ids=[])
        ],
        "discussion": "Discussion",
        "conclusion": "Conclusion",
    }
    kwargs.update(overrides)
    return ResearchDraft(**kwargs)


def _decision(**overrides: object) -> ChartGenerationDecision:
    kwargs: dict[str, object] = {
        "needs_charts": True,
        "charts": [
            ChartSpec(
                chart_type="bar",
                title="Adoption rate by year",
                data=[ChartDataPoint(label="2024", value=12.0)],
            )
        ],
        "reason": "The findings report a numeric adoption rate.",
    }
    kwargs.update(overrides)
    return ChartGenerationDecision(**kwargs)


@pytest.mark.asyncio
async def test_disabled_setting_never_calls_the_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "deep_research_chart_generation_enabled", False)
    runtime = AsyncMock()
    service = ChartGenerationService(cheap_generation_runtime=runtime, cheap_provider=None)

    decision = await service.decide(draft=_draft(), owner_id=uuid4(), research_run_id=uuid4())

    assert decision.needs_charts is False
    assert decision.charts == []
    runtime.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_enabled_setting_uses_the_cheap_provider_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "deep_research_chart_generation_enabled", True)
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=_decision())
    service = ChartGenerationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.decide(draft=_draft(), owner_id=uuid4(), research_run_id=uuid4())

    assert decision.needs_charts is True
    assert len(decision.charts) == 1
    runtime.execute.assert_awaited_once()
    assert runtime.execute.await_args.kwargs["provider"] == GenerationProvider.OPENAI


@pytest.mark.asyncio
async def test_falls_back_to_the_shared_runtime_when_no_cheap_provider_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "deep_research_chart_generation_enabled", True)
    cheap_runtime = AsyncMock()
    fallback_runtime = AsyncMock()
    fallback_runtime.execute.return_value = SimpleNamespace(
        parsed_output=_decision(needs_charts=False, charts=[], reason="No numeric data.")
    )
    service = ChartGenerationService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=None,
        fallback_generation_runtime=fallback_runtime,
    )

    decision = await service.decide(draft=_draft(), owner_id=uuid4(), research_run_id=uuid4())

    assert decision.needs_charts is False
    cheap_runtime.execute.assert_not_awaited()
    fallback_runtime.execute.assert_awaited_once()
    assert fallback_runtime.execute.await_args.kwargs["provider"] is None


@pytest.mark.asyncio
async def test_model_failure_fails_closed_to_no_charts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "deep_research_chart_generation_enabled", True)
    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("provider unavailable")
    service = ChartGenerationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.decide(draft=_draft(), owner_id=uuid4(), research_run_id=uuid4())

    assert decision.needs_charts is False
    assert decision.charts == []


@pytest.mark.asyncio
async def test_non_schema_valid_output_fails_closed_to_no_charts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "deep_research_chart_generation_enabled", True)
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(parsed_output=None)
    service = ChartGenerationService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )

    decision = await service.decide(draft=_draft(), owner_id=uuid4(), research_run_id=uuid4())

    assert decision.needs_charts is False
    assert decision.charts == []
