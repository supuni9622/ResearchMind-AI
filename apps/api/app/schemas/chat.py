# Chat request/response models.

from __future__ import annotations

from datetime import datetime
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


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    role: str
    content: str
    provider: str | None
    model: str | None
    created_at: datetime


class ChatConversationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversations: list[ChatConversationSummary]


class ChatConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    title: str | None
    messages: list[ChatMessageResponse]
