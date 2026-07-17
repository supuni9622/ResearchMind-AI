"""
Conversation artifact writer.
"""

from __future__ import annotations

import structlog

from app.ai.artifacts.conversation.models import ConversationIdentity, ConversationTurnArtifact
from app.ai.artifacts.writers.base import BaseArtifactWriter

logger = structlog.get_logger()


class ConversationArtifactWriter(BaseArtifactWriter):
    async def write_identity(
        self,
        identity: ConversationIdentity,
    ) -> None:
        """
        Writes `conversation.json` exactly once. Guarded by an `exists()`
        check on top of "only called at creation" (chat.py) -- belt and
        suspenders against ever overwriting it (PRD §5, Principle 1).
        """

        key = f"artifacts/conversations/{identity.conversation_id}/conversation.json"

        if await self._storage.exists(key=key):
            return

        try:
            await self._write_json(key=key, payload=identity)
        except Exception as exc:
            logger.exception(
                "artifacts.conversation.identity_write_failed",
                conversation_id=str(identity.conversation_id),
                exc_type=type(exc).__name__,
            )
            raise

    async def write_turn(
        self,
        turn: ConversationTurnArtifact,
    ) -> None:
        """
        Writes a fresh, never-overwritten `turns/{turn_id}/turn.json`
        per completed exchange (PRD §5, Principle 3 -- append-only).
        """

        key = (
            f"artifacts/conversations/{turn.metadata.conversation_id}"
            f"/turns/{turn.turn_id}/turn.json"
        )

        try:
            await self._write_json(key=key, payload=turn)
        except Exception as exc:
            logger.exception(
                "artifacts.conversation.turn_write_failed",
                conversation_id=str(turn.metadata.conversation_id),
                turn_id=str(turn.turn_id),
                exc_type=type(exc).__name__,
            )
            raise
