# Voice-on-Chat POC request models (docs/todo/voice-chat-poc-implementation-plan.md).

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.ai.runtime.generation.enums import GenerationProvider


class VoiceStreamRequest(BaseModel):
    """Handshake frame for `WS /chat/voice` -- same fields as
    `ChatStreamRequest` minus `user_prompt`, which arrives via streamed
    audio + Deepgram STT instead of a JSON field."""

    model_config = ConfigDict(extra="forbid")

    conversation_id: UUID | None = None

    provider: GenerationProvider | None = None

    web_search_enabled: bool = False

    paper_search_enabled: bool = False
