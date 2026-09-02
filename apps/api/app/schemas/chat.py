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

    # Only consulted when starting a new conversation (`conversation_id` is
    # None) -- an existing conversation keeps whatever project it already
    # belongs to. Authorized server-side before the conversation is created.
    project_id: UUID | None = None

    provider: GenerationProvider | None = None

    routing_strategy: RoutingStrategy | None = None

    # Toggle, set once per turn (persisted client-side, not server-side --
    # unlike Deep Research's mode enum, Chat has no DISABLED/REQUIRED
    # distinction, just on/off). No approval checkpoint: enabling this *is*
    # the approval, for every turn, since Chat has no interrupt/resume
    # mechanism to pause on (web_search_tool_platform_prd.md).
    web_search_enabled: bool = False

    # Same toggle-is-the-approval shape as `web_search_enabled`, but against
    # the Research Intelligence MCP server (prds/3. mcp_server_setup.md)
    # instead of Tavily -- searches papers relevant to this turn's
    # `user_prompt` and folds them into the answer + a sources list.
    paper_search_enabled: bool = False

    # Ids from prior `POST /chat/attachments` uploads, pre-uploaded because
    # `streamChat` builds one JSON body before opening the SSE stream.
    # `max_length` alone enforces Wave 4's "<=5/turn" (docs/
    # PRIORITIZED_ROADMAP.md).
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=5)


class ChatAttachmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    filename: str
    content_type: str
    url: str


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    role: str
    content: str
    provider: str | None
    model: str | None
    created_at: datetime
    attachments: list[ChatAttachmentResponse] = Field(default_factory=list)


class ChatConversationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    project_id: UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversations: list[ChatConversationSummary]
    next_cursor: UUID | None = None


class ChatConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID
    title: str | None
    messages: list[ChatMessageResponse]
    next_cursor: UUID | None = None
