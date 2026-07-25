"""Toggle-gated, no-approval web search for one Chat turn.

Reuses the same `WebSearchService`/`WebSearchNecessityService`/
`normalize_web_search_result` the Deep Research Runtime uses
(web_search_tool_platform_prd.md), but Chat has no LangGraph, no
interrupt/resume mechanism, and no product reason to block a fast
conversational turn on an approval click the way Deep Research's AUTO mode
does -- toggling web search on in Chat is itself the approval, once, up
front, for every turn in that conversation (mirrors Deep Research's
`web_search_auto_approve=True` behavior, minus the mode enum Chat doesn't
need: Chat has no REQUIRED/DISABLED distinction, just on/off).
"""

from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

import structlog
from pydantic import BaseModel, ConfigDict, Field

from app.ai.runtime.events.chat.models import ChatEventType
from app.ai.runtime.events.enums import EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.research.evidence import ResearchEvidenceBundle
from app.ai.runtime.research.retrieval.models import ResearchEvidenceReference
from app.ai.runtime.research.web_search.evidence import normalize_web_search_result
from app.ai.runtime.research.web_search.models import WebSearchMode
from app.ai.runtime.research.web_search.necessity import WebSearchNecessityService
from app.ai.tools.web_search.models import WebSearchRequest
from app.ai.tools.web_search.service import WebSearchService

logger = structlog.get_logger()

_MAX_CONTEXT_REFERENCES = 5
_MAX_EXCERPT_CHARACTERS = 400


class ChatWebSource(BaseModel):
    """Lightweight source descriptor for the frontend -- deliberately not
    the full `Citation`/`ResearchEvidenceReference` shape, since Chat has no
    citation-persistence mechanism today (no DB column, no artifact) and
    this is scoped to "show what was used for this turn", not durable
    citation tracking."""

    model_config = ConfigDict(extra="forbid")

    title: str
    url: str
    domain: str


class ChatWebSearchOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[StreamEvent] = Field(default_factory=list)
    context_text: str | None = None
    sources: list[ChatWebSource] = Field(default_factory=list)


def _format_web_context(references: list[ResearchEvidenceReference]) -> str:
    lines = [
        f"- {ref.filename}: {ref.excerpt[:_MAX_EXCERPT_CHARACTERS]}"
        for ref in references[:_MAX_CONTEXT_REFERENCES]
    ]
    return (
        "Web search results (use naturally in your answer; mention sources "
        "by name where relevant; never invent a URL or fact not present "
        "here):\n" + "\n".join(lines)
    )


async def run_chat_web_search(
    *,
    enabled: bool,
    user_prompt: str,
    owner_id: UUID,
    conversation_id: UUID,
    session_id: UUID,
    web_search: WebSearchService | None,
    web_search_necessity: WebSearchNecessityService | None,
) -> ChatWebSearchOutcome:
    """Best-effort: any failure here degrades to "no web search for this
    turn", never fails the chat turn itself (mirrors every other optional
    Chat collaborator -- memory, title generation, artifacts)."""

    if (
        not enabled
        or web_search is None
        or web_search_necessity is None
        or not web_search.available
    ):
        return ChatWebSearchOutcome()

    try:
        decision = await web_search_necessity.decide(
            mode=WebSearchMode.AUTO,
            goal=user_prompt,
            gap_question=None,
            evidence=ResearchEvidenceBundle(completed_task_count=0, failed_task_count=0),
            owner_id=owner_id,
            research_run_id=conversation_id,
        )
    except Exception as exc:
        logger.warning(
            "chat.web_search.necessity_failed",
            conversation_id=str(conversation_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return ChatWebSearchOutcome()

    if not decision.needs_web_search:
        return ChatWebSearchOutcome()

    events: list[StreamEvent] = [
        StreamEvent(
            session_id=session_id,
            category=EventCategory.TOOL,
            type=ChatEventType.CHAT_WEB_SEARCH_STARTED.value,
            metadata={"label": "Searching the web", "query": decision.query},
        )
    ]

    references: list[ResearchEvidenceReference] = []
    try:
        result = await web_search.search(WebSearchRequest(query=decision.query))
        references = await normalize_web_search_result(
            result,
            owner_id=owner_id,
            research_run_id=conversation_id,
        )
    except Exception as exc:
        logger.warning(
            "chat.web_search.failed",
            conversation_id=str(conversation_id),
            error_type=type(exc).__name__,
            error=str(exc),
        )

    if not references:
        events.append(
            StreamEvent(
                session_id=session_id,
                category=EventCategory.TOOL,
                type=ChatEventType.CHAT_WEB_SEARCH_SKIPPED.value,
                metadata={"label": "Web search returned nothing usable"},
            )
        )
        return ChatWebSearchOutcome(events=events)

    sources = [
        ChatWebSource(
            title=ref.filename,
            url=ref.document_id,
            domain=(urlsplit(ref.document_id).hostname or ref.filename),
        )
        for ref in references
    ]
    events.append(
        StreamEvent(
            session_id=session_id,
            category=EventCategory.TOOL,
            type=ChatEventType.CHAT_WEB_SEARCH_COMPLETED.value,
            metadata={
                "label": "Web search complete",
                "sources": [source.model_dump() for source in sources],
            },
        )
    )
    return ChatWebSearchOutcome(
        events=events,
        context_text=_format_web_context(references),
        sources=sources,
    )
