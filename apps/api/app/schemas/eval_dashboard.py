"""Response models for the internal eval dashboard (E7, EVALUATION_PLAN.md §16 phase 8)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.services.segment_analysis import ContentSegmentAggregate


class EvalScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    generation_id: uuid.UUID | None
    metric_name: str
    score: float | None
    passed: bool | None
    reason: str | None
    source: str
    sample_category: str | None
    dataset_example_id: str | None
    created_at: datetime


class EvalScoreListResponse(BaseModel):
    """Paginated page of one owner's `eval_scores` rows."""

    items: list[EvalScoreResponse]
    total: int
    limit: int
    offset: int


class OwnerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    owner_id: uuid.UUID
    email: str
    username: str | None
    score_count: int


class OwnerListResponse(BaseModel):
    """Paginated page of owners who have at least one `eval_scores` row."""

    items: list[OwnerSummary]
    total: int
    limit: int
    offset: int


class ReviewDecisionDistributionResponse(BaseModel):
    """Count of Deep Research `ResearchReview.decision` values for one owner."""

    owner_id: uuid.UUID
    counts: dict[str, int]


class OfflineExampleSummary(BaseModel):
    """One golden-set example with at least one offline-benchmark score."""

    dataset_example_id: str
    score_count: int
    latest_run_at: datetime


class OfflineExampleListResponse(BaseModel):
    """Paginated page of golden-set examples with offline-benchmark scores."""

    items: list[OfflineExampleSummary]
    total: int
    limit: int
    offset: int


class FingerprintSegmentAggregate(BaseModel):
    """One config-fingerprint value's aggregate score for a metric (E9, online half)."""

    fingerprint_value: str | None
    count: int
    avg_score: float | None
    pass_rate: float | None


class FingerprintSegmentAnalysisResponse(BaseModel):
    metric_name: str
    fingerprint_field: str
    items: list[FingerprintSegmentAggregate]


class ContentSegmentAnalysisResponse(BaseModel):
    """E9's offline half -- grouped by a golden-example field, not a fingerprint."""

    metric_name: str
    segment_field: str
    items: list[ContentSegmentAggregate]
