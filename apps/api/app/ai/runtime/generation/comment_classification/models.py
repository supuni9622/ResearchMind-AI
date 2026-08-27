from __future__ import annotations

from app.models.enums import CommentClassification
from pydantic import BaseModel, ConfigDict, Field


class CommentClassificationDecision(BaseModel):
    """
    Structured output of the cheap classification LLM call. Deliberately
    tiny, matching `WebSearchNecessityDecision`'s shape -- a fast/cheap
    model only needs to answer objective-or-preference plus a short,
    human-readable justification, never full reasoning.
    """

    model_config = ConfigDict(extra="forbid")

    classification: CommentClassification
    reason: str = Field(min_length=1, max_length=500)
