# Memory request/response models (memory_platform_prd.md §12/§13).

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from app.ai.memory.enums import MemoryScopeType, MemoryType
from app.core.settings import settings


class _MemoryScopeFields(BaseModel):
    scope_type: MemoryScopeType = MemoryScopeType.PERSONAL
    project_id: UUID | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> _MemoryScopeFields:
        if self.scope_type == MemoryScopeType.PROJECT and self.project_id is None:
            raise ValueError("project_id is required for project memory")
        if self.scope_type == MemoryScopeType.PERSONAL and self.project_id is not None:
            raise ValueError("project_id must be empty for personal memory")
        return self


def _metadata_depth(value: object, *, depth: int = 1) -> int:
    if isinstance(value, dict):
        return max(
            (_metadata_depth(item, depth=depth + 1) for item in value.values()),
            default=depth,
        )
    if isinstance(value, list):
        return max((_metadata_depth(item, depth=depth + 1) for item in value), default=depth)
    return depth


def _validate_metadata(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(encoded) > settings.memory_api_metadata_max_bytes:
        raise PydanticCustomError(
            "metadata_too_large",
            "metadata must be at most {max_bytes} encoded bytes",
            {"max_bytes": settings.memory_api_metadata_max_bytes},
        )
    if _metadata_depth(value) > settings.memory_api_metadata_max_depth:
        raise PydanticCustomError(
            "metadata_too_deep",
            "metadata nesting must be at most {max_depth} levels",
            {"max_depth": settings.memory_api_metadata_max_depth},
        )
    return value


# ==========================================================
# Requests
# ==========================================================


class MemoryRememberRequest(_MemoryScopeFields):
    model_config = ConfigDict(extra="forbid")

    type: MemoryType

    content: str = Field(min_length=1, max_length=settings.memory_api_content_max_characters)

    session_id: UUID | None = Field(
        default=None,
        description="Required when `type` is SESSION.",
    )

    metadata: dict[str, Any] = Field(default_factory=dict)

    _bounded_metadata = field_validator("metadata")(_validate_metadata)

    importance_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Overrides the computed importance score when supplied.",
    )


class MemorySearchApiRequest(_MemoryScopeFields):
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

    content: str | None = Field(default=None, max_length=settings.memory_api_content_max_characters)

    metadata: dict[str, Any] | None = None

    _bounded_metadata = field_validator("metadata")(_validate_metadata)

    importance_score: float | None = Field(default=None, ge=0.0, le=1.0)


# ==========================================================
# Responses
# ==========================================================


class MemoryRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID

    owner_id: UUID

    scope_type: MemoryScopeType

    project_id: UUID | None

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


class MemoryListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memories: list[MemoryRecordResponse]
    total: int
    limit: int
    offset: int


class MemoryContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_memories: list[MemoryRecordResponse]

    user_memories: list[MemoryRecordResponse]

    semantic_memories: list[MemoryRecordResponse]

    research_memories: list[MemoryRecordResponse]
