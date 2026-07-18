# Memory request/response models (memory_platform_prd.md §12/§13).

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.memory.enums import MemoryType

# ==========================================================
# Requests
# ==========================================================


class MemoryRememberRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MemoryType

    content: str = Field(min_length=1)

    session_id: UUID | None = Field(
        default=None,
        description="Required when `type` is SESSION.",
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    importance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overrides the computed importance score when supplied.",
    )


class MemorySearchApiRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)

    memory_types: list[MemoryType] = Field(
        default_factory=lambda: list(MemoryType),
    )

    top_k: int = Field(default=10, ge=1, le=100)


class MemoryUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: MemoryType | None = Field(
        default=None,
        description="Skips the multi-backend lookup when supplied.",
    )

    content: str | None = None

    metadata: dict[str, Any] | None = None

    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)


# ==========================================================
# Responses
# ==========================================================


class MemoryRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID

    owner_id: UUID

    type: MemoryType

    content: str

    metadata: dict[str, Any]

    importance_score: float

    created_at: datetime

    updated_at: datetime


class MemorySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memories: list[MemoryRecordResponse]

    latency_ms: float


class MemoryContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_memories: list[MemoryRecordResponse]

    semantic_memories: list[MemoryRecordResponse]

    research_memories: list[MemoryRecordResponse]
