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
    relevant_memory_ids: list[str] = Field(default_factory=list)
    allowed_memory_ids: list[str] = Field(default_factory=list)
    stale_memory_ids: list[str] = Field(default_factory=list)
    contradictory_memory_ids: list[str] = Field(default_factory=list)
    unsafe_memory_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ground_truth(self) -> MemoryEvaluationQuery:
        allowed = set(self.allowed_memory_ids)
        relevant = set(self.relevant_memory_ids)
        if not relevant <= allowed:
            raise ValueError("relevant_memory_ids must be a subset of allowed_memory_ids")
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
