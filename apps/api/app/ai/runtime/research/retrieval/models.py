"""Compact task evidence contracts; graph state must never contain full documents."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ResearchTaskStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    chunk_id: str
    filename: str
    citation_id: str | None = None
    score: float
    excerpt: str = Field(max_length=500)
    # Additive, defaulted field (web_search_tool_platform_prd.md) -- existing
    # checkpointed state (document-only evidence) still validates unchanged.
    # `document_id`/`chunk_id` hold a normalized URL / stable result id for
    # web evidence rather than a real document/chunk identifier.
    source_type: Literal["document", "web"] = "document"


class ResearchTaskResult(BaseModel):
    """Checkpoint-safe output for one task; detailed evidence remains in platforms/artifacts."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: ResearchTaskStatus
    retrieval_id: str | None = None
    evidence: list[ResearchEvidenceReference] = Field(default_factory=list, max_length=8)
    citation_ids: list[str] = Field(default_factory=list, max_length=8)
    error_type: str | None = None
