from __future__ import annotations

from enum import StrEnum


class ChatEventType(StrEnum):
    """Chat-owned event types for the (toggle-gated, no-approval) web search
    step -- mirrors `ResearchEventType`'s equivalent members, emitted with
    `category=EventCategory.TOOL` since these describe a tool call, not a
    token/generation event (web_search_tool_platform_prd.md)."""

    CHAT_WEB_SEARCH_STARTED = "chat_web_search_started"
    CHAT_WEB_SEARCH_COMPLETED = "chat_web_search_completed"
    CHAT_WEB_SEARCH_SKIPPED = "chat_web_search_skipped"
