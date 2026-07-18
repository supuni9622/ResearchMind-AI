"""
Canonical memory artifact models (PRD §22). Serialized to S3 under:

    memory/{owner_id}/{artifact_id}/{search,context}.json
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.ai.memory.enums import MemoryType
from app.ai.memory.models import MemoryContext, MemorySearchResult


class MemorySearchArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID = Field(default_factory=uuid4)

    version: str = Field(default="1.0")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    owner_id: UUID

    query: str

    memory_types: list[MemoryType]

    result: MemorySearchResult


class MemoryContextArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID = Field(default_factory=uuid4)

    version: str = Field(default="1.0")

    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    owner_id: UUID

    session_id: UUID | None = None

    context: MemoryContext
