from __future__ import annotations

from datetime import UTC, datetime

from app.models.conversation import Message
from app.models.enums import MessageRole
from app.services.conversation_compaction import compact_conversation_history


def _message(role: MessageRole, content: str) -> Message:
    now = datetime.now(UTC)
    return Message(
        role=role,
        content=content,
        conversation_id="00000000-0000-0000-0000-000000000001",
        created_at=now,
    )


def test_compaction_keeps_explicit_preference_and_bounds_output() -> None:
    summary = compact_conversation_history(
        existing_summary=None,
        messages=[
            _message(MessageRole.USER, "I prefer concise answers with examples."),
            _message(MessageRole.ASSISTANT, "I will keep answers practical and brief."),
            _message(MessageRole.USER, "Explain retrieval augmented generation in detail."),
        ],
        max_characters=1_000,
    )

    assert "Important user preferences or decisions" in summary
    assert "I prefer concise answers with examples." in summary
    assert "Earlier conversation highlights" in summary


def test_compaction_is_bounded() -> None:
    summary = compact_conversation_history(
        existing_summary="previous summary",
        messages=[_message(MessageRole.USER, "x" * 1_000)],
        max_characters=120,
    )

    assert len(summary) <= 150
