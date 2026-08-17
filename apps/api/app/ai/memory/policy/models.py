from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.memory.enums import MemoryScopeType


class MemoryExtractionAction(StrEnum):
    SKIP = "skip"
    EXTRACT_SYNC = "extract_sync"
    EXTRACT_ASYNC_READY = "extract_async_ready"


class MemoryTurnEvent(BaseModel):
    owner_id: UUID
    scope_type: MemoryScopeType = MemoryScopeType.PERSONAL
    project_id: UUID | None = None
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


class PreferenceSupersessionDecision(BaseModel):
    """
    Structured output of `PreferenceSupersessionService`'s cheap
    classification call: does a new USER preference statement replace one
    of the owner's existing ones?

    `superseded_index` is a required plain `int` (0 meaning "none"), not
    `int | None`, deliberately mirroring `_ExtractedMemoryLLM`'s docstring
    precedent -- an optional field with a default is absent from
    `required`, which OpenAI's strict structured-output mode rejects.
    """

    model_config = ConfigDict(extra="forbid")

    superseded_index: int = Field(
        description=(
            "1-indexed position of the existing preference this replaces "
            "in the numbered list, or 0 if it does not supersede any of "
            "them."
        ),
    )
    reason: str = Field(min_length=1, max_length=500)
