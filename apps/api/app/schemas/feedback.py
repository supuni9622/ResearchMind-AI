"""API request/response models for POST /feedback (EVALUATION_PLAN.md §16 phase 3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FeedbackRating, FeedbackSurface


class FeedbackCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generation_id: UUID = Field(
        description="GenerationResult.generation_id this feedback is about.",
    )

    surface: FeedbackSurface

    rating: FeedbackRating

    comment: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional free-text comment accompanying the rating.",
    )


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generation_id: UUID
    surface: FeedbackSurface
    rating: FeedbackRating
    comment: str | None
    created_at: datetime
    updated_at: datetime
