from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ConsolidationAction(StrEnum):
    DUPLICATE = "duplicate"
    MERGEABLE = "mergeable"
    CONTRADICTION = "contradiction"
    UNRELATED = "unrelated"


class ConsolidationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ConsolidationAction
    merged_content: str = Field(
        description="Merged factual statement for mergeable items; empty otherwise."
    )
    reason: str = Field(min_length=1, max_length=500)


class ConsolidationRunResult(BaseModel):
    examined: int = 0
    candidates: int = 0
    duplicates: int = 0
    merged: int = 0
    contradictions: int = 0
    unrelated: int = 0
    failed: int = 0
