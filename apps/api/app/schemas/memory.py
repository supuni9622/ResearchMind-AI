# Memory request/response models (memory_platform_prd.md §12/§13).

from __future__ import annotations

import json
from contextlib import suppress
from datetime import datetime
from enum import StrEnum
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
        if self.scope_type != MemoryScopeType.PROJECT and self.project_id is not None:
            raise ValueError("project_id must be empty for personal or global memory")
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


class MemoryOrigin(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class MemoryMoveRequest(_MemoryScopeFields):
    model_config = ConfigDict(extra="forbid")

    source_scope_type: MemoryScopeType = MemoryScopeType.PERSONAL
    source_project_id: UUID | None = None
    confirmed: bool

    @model_validator(mode="after")
    def validate_source_and_destination(self) -> MemoryMoveRequest:
        if self.source_scope_type == MemoryScopeType.PROJECT and self.source_project_id is None:
            raise ValueError("source_project_id is required for project memory")
        if self.source_scope_type != MemoryScopeType.PROJECT and self.source_project_id is not None:
            raise ValueError("source_project_id must be empty for personal or global memory")
        if (self.source_scope_type, self.source_project_id) == (self.scope_type, self.project_id):
            raise ValueError("destination scope must differ from source scope")
        return self


class MemoryScopeSettingsUpdate(_MemoryScopeFields):
    model_config = ConfigDict(extra="forbid")

    capture_enabled: bool
    retrieval_enabled: bool
    inherit_personal_memory: bool = True


# ==========================================================
# Responses
# ==========================================================


class MemoryRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID

    scope_type: MemoryScopeType

    project_id: UUID | None

    type: MemoryType

    content: str

    source: str | None = None
    confidence: float | None = None
    origin: MemoryOrigin
    last_used_at: datetime | None = None
    editable: bool

    created_at: datetime

    updated_at: datetime

    @classmethod
    def from_record(cls, record: Any) -> MemoryRecordResponse:
        metadata = record.metadata if isinstance(record.metadata, dict) else {}
        preference = metadata.get("preference")
        preference = preference if isinstance(preference, dict) else {}
        raw_confidence = preference.get("confidence", metadata.get("confidence"))
        confidence = (
            float(raw_confidence)
            if isinstance(raw_confidence, int | float) and not isinstance(raw_confidence, bool)
            else None
        )
        explicit = preference.get("explicit")
        source = preference.get("source") or metadata.get("source")
        origin = (
            MemoryOrigin.EXPLICIT
            if explicit is True or metadata.get("origin") == "explicit" or source == "manual"
            else MemoryOrigin.INFERRED
        )
        last_used_at = None
        raw_last_used = metadata.get("last_used_at")
        if isinstance(raw_last_used, str):
            with suppress(ValueError):
                last_used_at = datetime.fromisoformat(raw_last_used)
        return cls(
            id=record.id,
            scope_type=record.scope_type,
            project_id=record.project_id,
            type=record.type,
            content=record.content,
            source=str(source) if source is not None else None,
            confidence=confidence,
            origin=origin,
            last_used_at=last_used_at,
            editable=record.type != MemoryType.SESSION,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


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


class MemoryScopeSettingsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope_type: MemoryScopeType
    project_id: UUID | None
    capture_enabled: bool
    retrieval_enabled: bool
    inherit_personal_memory: bool
    retention_enabled: bool = True


class MemoryProjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    name: str
    role: str


class MemoryDeletionPreviewRequest(_MemoryScopeFields):
    model_config = ConfigDict(extra="forbid")

    memory_ids: list[UUID] | None = Field(default=None, max_length=1000)


class MemoryDeletionPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_token: str
    affected_count: int
    scope_type: MemoryScopeType
    project_id: UUID | None
    expires_at: datetime
    immediate_erasure: bool = True


class MemoryDeletionExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_token: str = Field(min_length=20, max_length=200)


class MemoryGovernanceJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    scope_type: MemoryScopeType
    project_id: UUID | None
    status: str
    requested_count: int
    deleted_postgres: int
    deleted_qdrant: int
    deleted_valkey: int
    deleted_artifacts: int
    failure_stage: str | None
    completed_at: datetime | None

    @classmethod
    def from_row(cls, row: Any) -> MemoryGovernanceJobResponse:
        return cls(
            id=row.id,
            scope_type=MemoryScopeType(row.scope_type),
            project_id=row.project_id,
            status=row.status,
            requested_count=row.requested_count,
            deleted_postgres=row.deleted_postgres,
            deleted_qdrant=row.deleted_qdrant,
            deleted_valkey=row.deleted_valkey,
            deleted_artifacts=row.deleted_artifacts,
            failure_stage=row.failure_stage,
            completed_at=row.completed_at,
        )


class MemoryPortableExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "researchmind.memory.export.v1"
    exported_at: datetime
    scope_type: MemoryScopeType
    project_id: UUID | None
    memories: list[MemoryRecordResponse]
