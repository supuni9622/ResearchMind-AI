"""
Conversation artifact reader -- reconstructs conversation history from
persisted ConversationTurnArtifacts.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.artifacts.conversation.models import ConversationTurnArtifact
from app.ai.artifacts.readers.base import BaseArtifactReader


class ConversationArtifactReader(BaseArtifactReader):
    async def list_turns(
        self,
        conversation_id: UUID,
    ) -> list[ConversationTurnArtifact]:
        """
        Enumerates every persisted turn via `storage.list_keys()` (no
        mutable index file to consult -- see module docstring on
        `conversation/models.py`), then sorts oldest-first.
        """

        prefix = f"artifacts/conversations/{conversation_id}/turns/"

        keys = await self._storage.list_keys(prefix=prefix)

        turns = [
            await self._read_json(key=key, model=ConversationTurnArtifact) for key in sorted(keys)
        ]

        return sorted(turns, key=lambda turn: turn.created_at)
