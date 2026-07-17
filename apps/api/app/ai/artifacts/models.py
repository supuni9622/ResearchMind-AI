from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ArtifactMetadata(BaseModel):
    """
    Canonical metadata embedded on every artifact (PRD §20).
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier of this artifact.",
    )

    version: str = Field(
        default="1.0",
        description="Artifact schema version.",
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the artifact was generated.",
    )

    owner_id: UUID | None = Field(
        default=None,
        description="User that owns the execution this artifact represents.",
    )

    session_id: UUID | None = Field(
        default=None,
        description="Session this execution belongs to, when known.",
    )


class JsonDictFile(BaseModel):
    """
    Generic single-object wrapper so a loosely-typed `dict[str, Any]`
    artifact field can still be written via `write_json_artifact`
    (which takes a `BaseModel`, not a bare dict). Used by the
    scaffold-only Research/Agent artifact modules, whose fields aren't
    tightly typed yet -- see their own module docstrings.
    """

    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
