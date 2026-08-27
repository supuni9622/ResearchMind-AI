from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.chat.web_search import run_chat_web_search
from app.ai.runtime.events.chat.models import ChatEventType
from app.ai.runtime.research.web_search.models import WebSearchNecessityDecision
from app.ai.tools.web_search.models import WebSearchResult, WebSearchResultItem
from app.ai.tools.web_search.service import WebSearchService


def _necessity(*, needs_web_search: bool, query: str = "current pricing") -> AsyncMock:
    necessity = AsyncMock()
    necessity.decide.return_value = WebSearchNecessityDecision(
        needs_web_search=needs_web_search, query=query, reason="reason"
    )
    return necessity


def _web_search(*, available: bool = True, search: AsyncMock | None = None) -> WebSearchService:
    fake = AsyncMock(spec=WebSearchService)
    fake.available = available
    fake.search = search or AsyncMock()
    return fake


@pytest.mark.asyncio
async def test_disabled_toggle_never_calls_the_necessity_service() -> None:
    necessity = _necessity(needs_web_search=True)
    outcome = await run_chat_web_search(
        enabled=False,
        user_prompt="what's new in AI",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(),
        web_search_necessity=necessity,
    )
    assert outcome.events == []
    assert outcome.context_text is None
    assert outcome.sources == []
    assert outcome.invoked is False
    necessity.decide.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_collaborators_degrade_to_no_search() -> None:
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="what's new in AI",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=None,
        web_search_necessity=_necessity(needs_web_search=True),
    )
    assert outcome.events == []
    assert outcome.invoked is False


@pytest.mark.asyncio
async def test_unavailable_web_search_service_degrades_to_no_search() -> None:
    necessity = _necessity(needs_web_search=True)
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="what's new in AI",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(available=False),
        web_search_necessity=necessity,
    )
    assert outcome.events == []
    assert outcome.invoked is False
    necessity.decide.assert_not_awaited()


@pytest.mark.asyncio
async def test_necessity_failure_degrades_gracefully() -> None:
    necessity = AsyncMock()
    necessity.decide.side_effect = RuntimeError("boom")
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="what's new in AI",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(),
        web_search_necessity=necessity,
    )
    assert outcome.events == []
    assert outcome.invoked is False


@pytest.mark.asyncio
async def test_decision_no_web_search_needed_never_calls_search() -> None:
    necessity = _necessity(needs_web_search=False)
    search = AsyncMock()
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="what's the capital of France",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(search=search),
        web_search_necessity=necessity,
    )
    assert outcome.events == []
    assert outcome.invoked is False
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_search_produces_events_context_and_sources() -> None:
    necessity = _necessity(needs_web_search=True, query="current pricing")
    result = WebSearchResult(
        query="current pricing",
        items=[
            WebSearchResultItem(
                title="Pricing page",
                url="https://example.com/pricing",
                snippet="Current pricing is $10/month.",
                provider="tavily",
                domain="example.com",
            )
        ],
        provider="tavily",
        duration_ms=5.0,
    )
    search = AsyncMock(return_value=result)
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="how much does it cost now",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(search=search),
        web_search_necessity=necessity,
    )

    event_types = [event.type for event in outcome.events]
    assert event_types == [
        ChatEventType.CHAT_WEB_SEARCH_STARTED.value,
        ChatEventType.CHAT_WEB_SEARCH_COMPLETED.value,
    ]
    assert outcome.context_text is not None
    assert "Pricing page" in outcome.context_text
    assert len(outcome.sources) == 1
    assert outcome.sources[0].domain == "example.com"
    assert outcome.sources[0].url == "https://example.com/pricing"
    assert outcome.invoked is True


@pytest.mark.asyncio
async def test_search_with_no_usable_results_emits_skipped_event() -> None:
    necessity = _necessity(needs_web_search=True)
    empty_result = WebSearchResult(query="q", items=[], provider="tavily", duration_ms=1.0)
    search = AsyncMock(return_value=empty_result)
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="anything new",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(search=search),
        web_search_necessity=necessity,
    )

    event_types = [event.type for event in outcome.events]
    assert event_types == [
        ChatEventType.CHAT_WEB_SEARCH_STARTED.value,
        ChatEventType.CHAT_WEB_SEARCH_SKIPPED.value,
    ]
    assert outcome.context_text is None
    assert outcome.sources == []
    # Invoked but unsuccessful -- distinct from the never-attempted cases
    # above, exactly the distinction E23's success-rate metric needs.
    assert outcome.invoked is True


@pytest.mark.asyncio
async def test_search_failure_degrades_to_skipped_event() -> None:
    necessity = _necessity(needs_web_search=True)
    search = AsyncMock(side_effect=RuntimeError("provider down"))
    outcome = await run_chat_web_search(
        enabled=True,
        user_prompt="anything new",
        owner_id=uuid4(),
        conversation_id=uuid4(),
        session_id=uuid4(),
        web_search=_web_search(search=search),
        web_search_necessity=necessity,
    )

    event_types = [event.type for event in outcome.events]
    assert event_types == [
        ChatEventType.CHAT_WEB_SEARCH_STARTED.value,
        ChatEventType.CHAT_WEB_SEARCH_SKIPPED.value,
    ]
    assert outcome.invoked is True
    # Invoked-but-failed (an exception mid-search) still counts as an
    # attempt for E23's invocation-rate metric, same as the empty-results
    # case above.
