"""API response models for user-scoped generation cost summaries."""

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
