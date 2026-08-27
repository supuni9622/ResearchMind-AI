"""
Canonical Memory Platform models (PRD §10).

`MemoryRecord` is the single unit every memory type is expressed as,
regardless of which storage backend actually holds it (Valkey for
SESSION, Postgres for USER/RESEARCH, Qdrant for SEMANTIC -- see
`create.py`). Callers never see provider-specific shapes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.memory.enums import MemoryScopeType, MemoryType


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID

    owner_id: UUID

    scope_type: MemoryScopeType = MemoryScopeType.PERSONAL

    project_id: UUID | None = None

    type: MemoryType

    content: str

    metadata: dict[str, Any] = Field(default_factory=dict)

    importance_score: float = Field(ge=0.0, le=1.0)

    created_at: datetime

    updated_at: datetime

    @model_validator(mode="after")
    def validate_scope(self) -> MemoryRecord:
        if self.scope_type == MemoryScopeType.PROJECT and self.project_id is None:
            raise ValueError("project_id is required for project-scoped memory")
        if self.scope_type == MemoryScopeType.PERSONAL and self.project_id is not None:
            raise ValueError("project_id must be empty for personal memory")
        return self


class MemorySearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)

    owner_id: UUID

    scope_type: MemoryScopeType = MemoryScopeType.PERSONAL

    project_id: UUID | None = None

    memory_types: list[MemoryType] = Field(
        default_factory=lambda: list(MemoryType),
    )

    top_k: int = Field(default=10, ge=1, le=100)

    @model_validator(mode="after")
    def validate_scope(self) -> MemorySearchRequest:
        if self.scope_type == MemoryScopeType.PROJECT and self.project_id is None:
            raise ValueError("project_id is required for project-scoped search")
        if self.scope_type == MemoryScopeType.PERSONAL and self.project_id is not None:
            raise ValueError("project_id must be empty for personal search")
        return self


class MemorySearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memories: list[MemoryRecord]

    latency_ms: float


class MemoryContext(BaseModel):
    """PRD §10 -- the bundle a consumer (chat, research, agent) pulls
    to ground a single turn."""

    model_config = ConfigDict(extra="forbid")

    session_memories: list[MemoryRecord] = Field(default_factory=list)

    user_memories: list[MemoryRecord] = Field(default_factory=list)

    semantic_memories: list[MemoryRecord] = Field(default_factory=list)

    research_memories: list[MemoryRecord] = Field(default_factory=list)


class ExtractedMemory(BaseModel):
    """
    PRD §17 -- output shape an LLM-driven extractor must produce.
    Consumed by future automatic memory generation; not yet wired to a
    live extraction pipeline (see memory_platform_prd.md §27 ordering,
    item 10).
    """

    model_config = ConfigDict(extra="forbid")

    content: str

    type: MemoryType

    importance: float = Field(ge=0.0, le=1.0)
