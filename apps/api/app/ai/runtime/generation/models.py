from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)
from typing import Any
from uuid import UUID, uuid4

from app.ai.knowledge.context.models import (
    PromptContext,
)
from app.ai.runtime.generation.enums import (
    GenerationOperation,
    GenerationProvider,
    PromptStrategy,
    ResponseFormat,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class GenerationRequest(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    prompt_context: PromptContext

    system_prompt: str | None = None

    user_prompt: str

    response_format: ResponseFormat = ResponseFormat.TEXT

    prompt_strategy: PromptStrategy = PromptStrategy.ZERO_SHOT

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )


class ProviderCapabilities(
    BaseModel,
):
    streaming: bool = True

    structured_output: bool = False

    tools: bool = False

    vision: bool = False

    reasoning: bool = False


class ModelMetadata(
    BaseModel,
):
    provider: GenerationProvider

    model: str

    context_window: int

    supports_json: bool

    supports_tools: bool

    cost_per_input_1m: float

    cost_per_output_1m: float


class GenerationStatistics(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    provider: GenerationProvider

    model: str

    latency_ms: float = 0

    prompt_tokens: int = 0

    completion_tokens: int = 0

    total_tokens: int = 0

    estimated_cost_usd: float = 0

    cache_hit: bool = False


class GenerationExecution(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    operation: GenerationOperation = GenerationOperation.GENERATE

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    completed_at: datetime | None = None


class GenerationResult(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
    )

    generation_id: UUID = Field(
        default_factory=uuid4,
    )

    request: GenerationRequest

    execution: GenerationExecution

    statistics: GenerationStatistics

    provider: GenerationProvider

    model: str

    content: str

    finish_reason: str | None = None

    metadata: dict[str, Any] = Field(
        default_factory=dict,
    )
