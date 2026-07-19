"""Compact SESSION-state records; never a second copy of conversation history."""

from __future__ import annotations

import re
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.settings import settings


class SessionStateMemory(BaseModel):
    kind: Literal["active_goal", "working_constraint", "pending_clarification"]
    content: str = Field(min_length=1)
    source_turn_id: str
    source_user_message_id: UUID | None = None
    source_assistant_message_id: UUID | None = None

    def metadata(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "source_turn_id": self.source_turn_id,
            **(
                {"source_user_message_id": str(self.source_user_message_id)}
                if self.source_user_message_id
                else {}
            ),
            **(
                {"source_assistant_message_id": str(self.source_assistant_message_id)}
                if self.source_assistant_message_id
                else {}
            ),
        }


def state_from_user_turn(
    *,
    user_message: str,
    source_turn_id: str,
    source_user_message_id: UUID | None = None,
    source_assistant_message_id: UUID | None = None,
) -> SessionStateMemory | None:
    """Persist only an explicit, temporary working state from a turn.

    Complete Q/A text remains in Conversation/Research persistence. This is
    deliberately conservative until a dedicated state updater is introduced.
    """

    normalized = " ".join(user_message.split())
    match = re.search(
        (
            r"(?i)\b(?:current goal is|focus on|for this session,? use|"
            r"keep this constraint)\b\s*:?[ ]*(.+)"
        ),
        normalized,
    )
    if match is None:
        return None
    content = match.group(1).strip()[: settings.memory_context_item_max_characters]
    if not content:
        return None
    return SessionStateMemory(
        kind="active_goal",
        content=content,
        source_turn_id=source_turn_id,
        source_user_message_id=source_user_message_id,
        source_assistant_message_id=source_assistant_message_id,
    )
