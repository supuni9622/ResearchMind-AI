"""API response models for user-scoped generation cost summaries."""

from uuid import UUID

from pydantic import BaseModel


class GenerationUsageSummary(BaseModel):
    total_cost_usd: float
    total_requests: int
    total_tokens: int
    month_cost_usd: float
    month_requests: int
    month_tokens: int
    memory_extraction_cost_usd: float
    memory_extraction_requests: int
    answer_turns: int
    memory_extraction_cost_per_100_turns: float


class ConversationUsageSummary(BaseModel):
    """Cost rollup for one research conversation's Linear Research turns.

    Deep Research runs are billed per-run, not per-conversation (see
    `PRODUCT_FLOWS_AND_GAPS.md`'s Linear Research Performance section) and
    are not included in this total.
    """

    conversation_id: UUID
    total_cost_usd: float
    total_requests: int
    total_tokens: int
