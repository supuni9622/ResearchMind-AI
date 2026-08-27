from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.chat.paper_query import PaperQueryExtractionResult, PaperQueryExtractionService
from app.ai.runtime.chat.paper_search import run_chat_paper_search
from app.ai.runtime.events.chat.models import ChatEventType
from app.ai.tools.paper_search.models import (
    PaperSearchRequest,
    PaperSearchResult,
    PaperSearchResultItem,
)
from app.ai.tools.paper_search.service import PaperSearchService


def _paper_search(*, available: bool = True, search: AsyncMock | None = None) -> PaperSearchService:
    fake = AsyncMock(spec=PaperSearchService)
    fake.available = available
    fake.search = search or AsyncMock()
    return fake


def _query_extraction(*, query: str = "extracted topic") -> AsyncMock:
    extraction = AsyncMock(spec=PaperQueryExtractionService)
    extraction.extract_details.return_value = PaperQueryExtractionResult(query=query)
    return extraction


@pytest.mark.asyncio
async def test_disabled_toggle_never_calls_search() -> None:
    search = AsyncMock()
    outcome = await run_chat_paper_search(
        enabled=False,
        user_prompt="what's new in retrieval augmented generation",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
    )
    assert outcome.events == []
    assert outcome.context_text is None
    assert outcome.sources == []
    assert outcome.invoked is False
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_collaborator_degrades_to_no_search() -> None:
    outcome = await run_chat_paper_search(
        enabled=True,
        user_prompt="what's new in retrieval augmented generation",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=None,
    )
    assert outcome.events == []
    assert outcome.invoked is False


@pytest.mark.asyncio
async def test_unavailable_service_degrades_to_no_search() -> None:
    search = AsyncMock()
    outcome = await run_chat_paper_search(
        enabled=True,
        user_prompt="what's new in retrieval augmented generation",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(available=False, search=search),
    )
    assert outcome.events == []
    assert outcome.invoked is False
    search.assert_not_awaited()


@pytest.mark.asyncio
async def test_successful_search_produces_events_context_and_sources() -> None:
    result = PaperSearchResult(
        query="retrieval augmented generation",
        items=[
            PaperSearchResultItem(
                title="RAG for Knowledge-Intensive NLP Tasks",
                authors=["P. Lewis"],
                year=2020,
                url="https://example.com/rag",
                abstract="We explore RAG models.",
            )
        ],
        provider="research_intelligence_mcp",
        duration_ms=5.0,
    )
    search = AsyncMock(return_value=result)
    outcome = await run_chat_paper_search(
        enabled=True,
        user_prompt="tell me about retrieval augmented generation",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
    )

    event_types = [event.type for event in outcome.events]
    assert event_types == [
        ChatEventType.CHAT_PAPER_SEARCH_STARTED.value,
        ChatEventType.CHAT_PAPER_SEARCH_COMPLETED.value,
    ]
    assert outcome.context_text is not None
    assert "RAG for Knowledge-Intensive NLP Tasks" in outcome.context_text
    assert len(outcome.sources) == 1
    assert outcome.sources[0].year == 2020
    assert outcome.invoked is True
    search.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_with_no_usable_results_emits_skipped_event() -> None:
    empty_result = PaperSearchResult(
        query="q", items=[], provider="research_intelligence_mcp", duration_ms=1.0
    )
    search = AsyncMock(return_value=empty_result)
    outcome = await run_chat_paper_search(
        enabled=True,
        user_prompt="anything new",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
    )

    event_types = [event.type for event in outcome.events]
    assert event_types == [
        ChatEventType.CHAT_PAPER_SEARCH_STARTED.value,
        ChatEventType.CHAT_PAPER_SEARCH_SKIPPED.value,
    ]
    assert outcome.context_text is None
    assert outcome.sources == []
    assert outcome.invoked is True


@pytest.mark.asyncio
async def test_search_failure_degrades_to_skipped_event() -> None:
    search = AsyncMock(side_effect=RuntimeError("mcp server down"))
    outcome = await run_chat_paper_search(
        enabled=True,
        user_prompt="anything new",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
    )

    event_types = [event.type for event in outcome.events]
    assert event_types == [
        ChatEventType.CHAT_PAPER_SEARCH_STARTED.value,
        ChatEventType.CHAT_PAPER_SEARCH_SKIPPED.value,
    ]
    assert outcome.invoked is True


@pytest.mark.asyncio
async def test_query_extraction_result_is_used_as_the_search_query() -> None:
    """Regression coverage for the production bug (2026-07-25): sending the
    raw chat message straight to search_papers returned zero results for
    conversational phrasing / meta-requests. When a query-extraction
    collaborator is provided, its distilled topic -- not the raw prompt --
    must be what's actually searched."""

    search = AsyncMock(
        return_value=PaperSearchResult(
            query="earthquake mechanisms",
            items=[PaperSearchResultItem(title="Earthquakes and friction laws")],
            provider="research_intelligence_mcp",
            duration_ms=1.0,
        )
    )
    extraction = _query_extraction(query="earthquake mechanisms")

    await run_chat_paper_search(
        enabled=True,
        user_prompt="why do earthquakes happen and what causes them",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
        query_extraction=extraction,
    )

    extraction.extract_details.assert_awaited_once()
    search.assert_awaited_once_with(PaperSearchRequest(query="earthquake mechanisms"))


@pytest.mark.asyncio
async def test_explicit_extracted_year_range_is_sent_to_search() -> None:
    search = AsyncMock(
        return_value=PaperSearchResult(
            query="earthquake mechanisms",
            items=[],
            provider="research_intelligence_mcp",
            duration_ms=1.0,
        )
    )
    extraction = _query_extraction(query="earthquake mechanisms")
    extraction.extract_details.return_value = PaperQueryExtractionResult(
        query="earthquake mechanisms", year_from=2018, year_to=2020
    )

    await run_chat_paper_search(
        enabled=True,
        user_prompt="earthquake papers from 2018 to 2020",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
        query_extraction=extraction,
    )

    search.assert_awaited_once_with(
        PaperSearchRequest(query="earthquake mechanisms", year_from=2018, year_to=2020)
    )


@pytest.mark.asyncio
async def test_missing_query_extraction_falls_back_to_the_raw_prompt() -> None:
    search = AsyncMock(
        return_value=PaperSearchResult(
            query="q", items=[], provider="research_intelligence_mcp", duration_ms=1.0
        )
    )

    await run_chat_paper_search(
        enabled=True,
        user_prompt="retrieval augmented generation",
        owner_id=uuid4(),
        session_id=uuid4(),
        paper_search=_paper_search(search=search),
        query_extraction=None,
    )

    search.assert_awaited_once_with(PaperSearchRequest(query="retrieval augmented generation"))
