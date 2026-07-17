"""
Conversation artifact builder. Pure -- no knowledge of storage.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.ai.artifacts.conversation.models import (
    ConversationArtifactMetadata,
    ConversationTurnArtifact,
)


class ConversationTurnArtifactBuilder:
    def build(
        self,
        *,
        conversation_id: UUID,
        owner_id: UUID,
        user_prompt: str,
        assistant_content: str,
        provider: str | None = None,
        model: str | None = None,
    ) -> ConversationTurnArtifact:

        return ConversationTurnArtifact(
            metadata=ConversationArtifactMetadata(
                owner_id=owner_id,
                conversation_id=conversation_id,
            ),
            user_prompt=user_prompt,
            assistant_content=assistant_content,
            provider=provider,
            model=model,
            created_at=datetime.now(UTC),
        )
