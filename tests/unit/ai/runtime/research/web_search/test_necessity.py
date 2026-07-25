from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.web_search.models import WebSearchMode, WebSearchNecessityDecision
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService


def _empty_bundle() -> ResearchEvidenceBundle:
    return ResearchEvidenceBundle(completed_task_count=1, failed_task_count=0)


@pytest.mark.asyncio
async def test_disabled_mode_never_calls_the_model() -> None:
    runtime = AsyncMock()
    service = WebSearchNecessityService(cheap_generation_runtime=runtime, cheap_provider=None)
    decision = await service.decide(
        mode=WebSearchMode.DISABLED,
        goal="goal",
        gap_question=None,
        evidence=_empty_bundle(),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )
    assert decision.needs_web_search is False
    runtime.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_required_mode_never_calls_the_model() -> None:
    runtime = AsyncMock()
    service = WebSearchNecessityService(cheap_generation_runtime=runtime, cheap_provider=None)
    decision = await service.decide(
        mode=WebSearchMode.REQUIRED,
        goal="goal",
        gap_question="what changed recently?",
        evidence=_empty_bundle(),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )
    assert decision.needs_web_search is True
    assert decision.query == "what changed recently?"
    runtime.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_auto_mode_uses_the_cheap_provider_when_configured() -> None:
    runtime = AsyncMock()
    runtime.execute.return_value = SimpleNamespace(
        parsed_output=WebSearchNecessityDecision(
            needs_web_search=True, query="current pricing", reason="private docs are outdated"
        ),
    )
    service = WebSearchNecessityService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )
    decision = await service.decide(
        mode=WebSearchMode.AUTO,
        goal="goal",
        gap_question="what changed recently?",
        evidence=_empty_bundle(),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )
    assert decision.needs_web_search is True
    assert decision.query == "current pricing"
    runtime.execute.assert_awaited_once()
    assert runtime.execute.await_args.kwargs["provider"] == GenerationProvider.OPENAI


@pytest.mark.asyncio
async def test_auto_mode_falls_back_to_the_shared_runtime_when_no_cheap_provider_configured() -> (
    None
):
    cheap_runtime = AsyncMock()
    fallback_runtime = AsyncMock()
    fallback_runtime.execute.return_value = SimpleNamespace(
        parsed_output=WebSearchNecessityDecision(
            needs_web_search=False, query="q", reason="private docs are sufficient"
        ),
    )
    service = WebSearchNecessityService(
        cheap_generation_runtime=cheap_runtime,
        cheap_provider=None,
        fallback_generation_runtime=fallback_runtime,
    )
    decision = await service.decide(
        mode=WebSearchMode.AUTO,
        goal="goal",
        gap_question=None,
        evidence=_empty_bundle(),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )
    assert decision.needs_web_search is False
    cheap_runtime.execute.assert_not_awaited()
    fallback_runtime.execute.assert_awaited_once()
    assert fallback_runtime.execute.await_args.kwargs["provider"] is None


@pytest.mark.asyncio
async def test_model_failure_fails_closed_to_no_search() -> None:
    runtime = AsyncMock()
    runtime.execute.side_effect = RuntimeError("provider unavailable")
    service = WebSearchNecessityService(
        cheap_generation_runtime=runtime, cheap_provider=GenerationProvider.OPENAI
    )
    decision = await service.decide(
        mode=WebSearchMode.AUTO,
        goal="goal",
        gap_question=None,
        evidence=_empty_bundle(),
        owner_id=uuid4(),
        research_run_id=uuid4(),
    )
    assert decision.needs_web_search is False
