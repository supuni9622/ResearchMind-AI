"""Versioned ground-truth dataset for offline memory evaluation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryEvaluationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    query: str
    category: str
    credential_key: str = "default"
    scope_type: str = "personal"
    project_key: str | None = None
    session_key: str = "default"
    memory_types: list[str] = Field(default_factory=lambda: ["user", "semantic", "research"])
    top_k: int = Field(default=5, ge=1, le=100)
    inherit_personal_user_memory: bool = True
    relevant_memory_ids: list[str] = Field(default_factory=list)
    allowed_memory_ids: list[str] = Field(default_factory=list)
    stale_memory_ids: list[str] = Field(default_factory=list)
    contradictory_memory_ids: list[str] = Field(default_factory=list)
    unsafe_memory_ids: list[str] = Field(default_factory=list)
    reference_answer: str | None = None
    answer_rubric: str | None = None

    @model_validator(mode="after")
    def validate_ground_truth(self) -> MemoryEvaluationQuery:
        allowed = set(self.allowed_memory_ids)
        relevant = set(self.relevant_memory_ids)
        if not relevant <= allowed:
            raise ValueError("relevant_memory_ids must be a subset of allowed_memory_ids")
        if self.scope_type not in {"personal", "project"}:
            raise ValueError("scope_type must be personal or project")
        if self.scope_type == "project" and self.project_key is None:
            raise ValueError("project_key is required for project-scoped queries")
        if self.scope_type == "personal" and self.project_key is not None:
            raise ValueError("project_key must be empty for personal queries")
        return self


class MemoryEvaluationDataset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str
    notes: str = ""
    queries: list[MemoryEvaluationQuery]


def load_memory_evaluation_dataset(path: Path) -> MemoryEvaluationDataset:
    if not path.exists():
        raise FileNotFoundError(f"Memory evaluation dataset not found: {path}")
    return MemoryEvaluationDataset.model_validate(json.loads(path.read_text(encoding="utf-8")))
