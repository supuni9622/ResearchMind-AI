"""Toggle-gated, no-approval paper search for one Chat turn.

Reuses `PaperSearchService` (Research Intelligence MCP, prds/3.
mcp_server_setup.md) the same way `run_chat_web_search` reuses
`WebSearchService`. Toggling this on always searches -- no necessity-
decision *gate* (Chat has no LangGraph/interrupt mechanism, and the
toggle itself is the approval, every turn) -- but the search *query* is
distilled from `user_prompt` via `PaperQueryExtractionService` rather than
sent raw: confirmed in production (2026-07-25) that a raw conversational
sentence or a meta-request like "can I have research papers" returns zero
results from `search_papers`, since neither reads as a topic to an
academic search backend. `query_extraction` is optional -- when absent
(or it fails internally, which it handles itself, degrading to the raw
prompt) this still works, just with the weaker raw-prompt query. Best-
effort throughout: any failure degrades to "no papers for this turn,"
never fails the chat turn (mirrors every other optional Chat collaborator
-- memory, title generation, web search).
"""

from __future__ import annotations

from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.ai.runtime.chat.paper_query import PaperQueryExtractionService
from app.ai.runtime.events.chat.models import ChatEventType
from app.ai.runtime.events.enums import EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.tools.paper_search.models import PaperSearchRequest, PaperSearchResultItem
from app.ai.tools.paper_search.service import PaperSearchService

logger = structlog.get_logger()

_MAX_QUERY_CHARACTERS = 500
_MAX_CONTEXT_ITEMS = 5
_MAX_ABSTRACT_CHARACTERS = 400


class ChatPaperSource(BaseModel):
    """Lightweight source descriptor for the frontend -- mirrors
    `ChatWebSource`: this is "what was used for this turn," not durable
    citation tracking."""

    model_config = ConfigDict(extra="forbid")

    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    url: str | None = None


class ChatPaperSearchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[StreamEvent] = Field(default_factory=list)
    context_text: str | None = None
    sources: list[ChatPaperSource] = Field(default_factory=list)
    invoked: bool = False
    """True once the search call was actually attempted -- paper search
    has no necessity gate (unlike web search, the toggle itself is the
    only gate), so this is True whenever `enabled` and the service is
    available. See `ChatWebSearchOutcome.invoked`'s docstring for why
    this is tracked separately from `context_text is None`."""


def _format_paper_context(items: list[PaperSearchResultItem]) -> str:
    lines = []
    for item in items[:_MAX_CONTEXT_ITEMS]:
        authors = ", ".join(item.authors[:3]) if item.authors else "Unknown authors"
        year = f" ({item.year})" if item.year else ""
        abstract = (item.abstract or "")[:_MAX_ABSTRACT_CHARACTERS]
        lines.append(f"- {item.title} -- {authors}{year}: {abstract}")
    return (
        "Related research papers (use naturally in your answer; mention "
        "papers by title where relevant; never invent a paper or fact not "
        "present here):\n" + "\n".join(lines)
    )


async def run_chat_paper_search(
    *,
    enabled: bool,
    user_prompt: str,
    owner_id: UUID,
    session_id: UUID,
    paper_search: PaperSearchService | None,
    query_extraction: PaperQueryExtractionService | None = None,
    conversation_context: str | None = None,
) -> ChatPaperSearchOutcome:
    """Best-effort: any failure here degrades to "no paper search for this
    turn", never raises."""

    if not enabled or paper_search is None or not paper_search.available:
        return ChatPaperSearchOutcome()

    if query_extraction is not None:
        extracted = await query_extraction.extract_details(
            user_prompt=user_prompt,
            owner_id=owner_id,
            session_id=session_id,
            conversation_context=conversation_context,
        )
        query = extracted.query
        year_from = extracted.year_from
        year_to = extracted.year_to
    else:
        query = user_prompt.strip()[:_MAX_QUERY_CHARACTERS]
        year_from = None
        year_to = None

    events: list[StreamEvent] = [
        StreamEvent(
            session_id=session_id,
            category=EventCategory.TOOL,
            type=ChatEventType.CHAT_PAPER_SEARCH_STARTED.value,
            metadata={"label": "Searching research papers", "query": query},
        )
    ]

    items: list[PaperSearchResultItem] = []
    try:
        result = await paper_search.search(
            PaperSearchRequest(query=query, year_from=year_from, year_to=year_to)
        )
        items = result.items
    except Exception as exc:
        logger.warning(
            "chat.paper_search.failed",
            session_id=str(session_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )

    if not items:
        events.append(
            StreamEvent(
                session_id=session_id,
                category=EventCategory.TOOL,
                type=ChatEventType.CHAT_PAPER_SEARCH_SKIPPED.value,
                metadata={"label": "Paper search returned nothing usable"},
            )
        )
        return ChatPaperSearchOutcome(events=events, invoked=True)

    sources = [
        ChatPaperSource(title=item.title, authors=item.authors, year=item.year, url=item.url)
        for item in items
    ]
    events.append(
        StreamEvent(
            session_id=session_id,
            category=EventCategory.TOOL,
            type=ChatEventType.CHAT_PAPER_SEARCH_COMPLETED.value,
            metadata={
                "label": "Paper search complete",
                "sources": [source.model_dump() for source in sources],
            },
        )
    )
    return ChatPaperSearchOutcome(
        events=events,
        context_text=_format_paper_context(items),
        sources=sources,
        invoked=True,
    )
