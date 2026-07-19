from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field


class MemoryExtractionAction(StrEnum):
    SKIP = "skip"
    EXTRACT_SYNC = "extract_sync"
    EXTRACT_ASYNC_READY = "extract_async_ready"


class MemoryTurnEvent(BaseModel):
    owner_id: UUID
    session_id: UUID
    runtime: str
    user_message: str
    assistant_message: str
    turn_id: str
    conversation_id: UUID | None = None
    research_id: UUID | None = None
    is_final_user_facing_turn: bool = True


class MemoryExtractionDecision(BaseModel):
    action: MemoryExtractionAction
    reasons: list[str] = Field(default_factory=list)
    explicit_request: bool = False
    promotion_topics: list[str] = Field(default_factory=list)


class MemoryExtractionOutcome(BaseModel):
    decision: MemoryExtractionDecision
    extracted_count: int = 0
    created_count: int = 0
    updated_count: int = 0
    duplicate_count: int = 0
    skipped_count: int = 0
    failed: bool = False
