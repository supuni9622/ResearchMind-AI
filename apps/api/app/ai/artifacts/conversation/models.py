"""
Conversation artifact models (PRD §15, adapted).

Storage layout:

    artifacts/conversations/{conversation_id}/
        conversation.json           (written once, at creation)
        turns/{turn_id}/turn.json   (written once per completed turn)

Diverges from the PRD's literal `messages.json`/`summary.json` files:
overwriting a fixed `messages.json` on every turn would violate the
Artifact Platform's own immutability principle (PRD §5, Principle 1),
so each turn gets its own immutable file instead (Principle 3,
append-only). `summary.json` is out of scope -- no summarization
component exists yet in this codebase to produce one.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.artifacts.models import ArtifactMetadata


class ConversationIdentity(BaseModel):
    """Written once as `conversation.json` -- mirrors the `Conversation` row."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID

    owner_id: UUID

    title: str | None = None

    created_at: datetime


class ConversationArtifactMetadata(ArtifactMetadata):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID


class ConversationTurnArtifact(BaseModel):
    """
    Canonical persistence model for one completed user/assistant
    exchange. A fresh `turn_id` every write -- see module docstring.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: ConversationArtifactMetadata

    turn_id: UUID = Field(default_factory=uuid4)

    user_prompt: str

    assistant_content: str

    provider: str | None = None

    model: str | None = None

    created_at: datetime
