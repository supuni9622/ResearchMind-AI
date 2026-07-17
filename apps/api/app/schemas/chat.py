# Chat request/response models.

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.routing.enums import RoutingStrategy


class ChatStreamRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_prompt: str = Field(min_length=1)

    conversation_id: UUID | None = None

    provider: GenerationProvider | None = None

    routing_strategy: RoutingStrategy | None = None
