"""Captured retrieval/injection results kept separate from M6 ground truth."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class MemoryQueryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    retrieved_memory_ids: list[str] = Field(default_factory=list)
    selected_memory_ids: list[str] = Field(default_factory=list)
    latency_ms: float = Field(ge=0)
    selected_tokens: int = Field(default=0, ge=0)


class MemoryCandidateResults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: str
    version: str
    dataset_version: str
    results: list[MemoryQueryResult]


def load_memory_candidate_results(path: Path) -> MemoryCandidateResults:
    if not path.exists():
        raise FileNotFoundError(f"Memory candidate results not found: {path}")
    return MemoryCandidateResults.model_validate(json.loads(path.read_text(encoding="utf-8")))
