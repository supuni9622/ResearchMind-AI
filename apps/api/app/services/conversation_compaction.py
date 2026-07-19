"""Deterministic, zero-provider-cost compaction for Chat prompt history."""

from __future__ import annotations

import re

from app.models.conversation import Message
from app.models.enums import MessageRole

_WHITESPACE = re.compile(r"\s+")
_INTEREST_MARKERS = (
    "i prefer",
    "i am interested",
    "i'm interested",
    "i am learning",
    "i'm learning",
    "i am researching",
    "i'm researching",
    "remember",
    "from now on",
    "we decided",
    "our decision",
)


def _excerpt(content: str, *, limit: int) -> str:
    normalized = _WHITESPACE.sub(" ", content).strip()
    return normalized if len(normalized) <= limit else f"{normalized[: limit - 1].rstrip()}…"


def compact_conversation_history(
    *,
    existing_summary: str | None,
    messages: list[Message],
    max_characters: int,
) -> str:
    """Create a bounded structured record without an additional LLM call.

    The canonical messages stay in PostgreSQL and remain available through the
    paginated replay API. This summary is only the compressed model-context
    representation of compacted turns. Explicit preferences and decisions are
    retained before general turn excerpts so they survive repeated compaction.
    """

    important_user_lines: list[str] = []
    turn_lines: list[str] = []

    for message in messages:
        content = _excerpt(message.content, limit=220)
        if message.role == MessageRole.USER:
            if any(marker in content.lower() for marker in _INTEREST_MARKERS):
                important_user_lines.append(f"- {content}")
            else:
                turn_lines.append(f"- User asked: {content}")
        else:
            turn_lines.append(f"- Assistant covered: {content}")

    sections: list[str] = []
    if important_user_lines:
        sections.append(
            "Important user preferences or decisions:\n" + "\n".join(important_user_lines)
        )
    if existing_summary:
        sections.append(existing_summary.strip())
    if turn_lines:
        sections.append("Earlier conversation highlights:\n" + "\n".join(turn_lines))

    summary = "\n\n".join(section for section in sections if section)
    if len(summary) <= max_characters:
        return summary

    # Preference/decision evidence is deliberately ordered first so it remains
    # available even when the bounded summary must be trimmed.
    retained = summary[: max_characters - len("[Earlier compacted context]\n")]
    return f"[Earlier compacted context]\n{retained.rstrip()}"
