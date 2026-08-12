"""Response/request models for E10's promotion-review queue
(EVALUATION_PLAN.md §3/§15)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FailureCategoryLiteral = Literal[
    "wrong_citation",
    "hallucination",
    "retrieval_miss",
    "unnecessary_tool_use",
    "abstention_failure",
    "workflow_loop",
    "schema_violation",
    "injection_success",
]

QueryTypeLiteral = Literal["factual", "synthesis", "comparison", "exploratory", "unanswerable"]
DifficultyLiteral = Literal["easy", "medium", "hard"]
WorkflowLiteral = Literal["chat", "linear_research", "deep_research"]


class PromotionCandidateResponse(BaseModel):
    source: str
    owner_id: uuid.UUID
    generation_id: uuid.UUID
    reason: str
    created_at: datetime


class PromotionCandidateListResponse(BaseModel):
    items: list[PromotionCandidateResponse]
    total: int
    limit: int
    offset: int


class TraceUrlResponse(BaseModel):
    trace_url: str | None


class RejectPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    owner_id: uuid.UUID
    generation_id: uuid.UUID


class ConfirmPromotionRequest(BaseModel):
    """
    Everything a reviewer fills in by hand after reading the real content
    via the LangSmith trace link -- this API never sees the original
    question/answer/context itself. Field shapes mirror
    `benchmarks.generation.golden_dataset.GoldenExample` so
    `sync_promoted_examples.py` can construct one directly.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    direction: Literal["failure", "good"]
    owner_id: uuid.UUID
    generation_id: uuid.UUID

    question: str = Field(min_length=1)
    reference_answer: str = Field(min_length=1)
    contexts: list[str] = Field(min_length=1)
    reference_context_ids: list[str] = Field(default_factory=list)
    expected_citation_ids: list[str] = Field(default_factory=list)
    query_type: QueryTypeLiteral
    difficulty: DifficultyLiteral
    workflow: WorkflowLiteral
    rubric: str | None = None
    failure_category: FailureCategoryLiteral | None = None
    """Required for `direction="failure"`, forbidden for `"good"` --
    enforced in the route, not here, since a cross-field conditional
    requirement reads more clearly as an explicit check than a Pydantic
    validator for a form this small."""


class PromotionReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source: str
    direction: str
    owner_id: uuid.UUID
    generation_id: uuid.UUID
    status: str
    reviewed_by: uuid.UUID
    reviewed_at: datetime
    synced: bool
