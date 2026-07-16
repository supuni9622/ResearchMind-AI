from __future__ import annotations

from datetime import (
    UTC,
    datetime,
)
from enum import StrEnum
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


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class StreamEventType(StrEnum):
    START = "start"
    TOKEN = "token"
    TOOL_CALL = "tool_call"
    COMPLETED = "completed"
    ERROR = "error"


class GenerationRequest(BaseModel):
    prompt_context: PromptContext

    user_prompt: str

    system_prompt: str | None = None

    response_format: ResponseFormat = ResponseFormat.TEXT

    prompt_strategy: PromptStrategy = PromptStrategy.ZERO_SHOT

    temperature: float | None = None

    max_tokens: int | None = None

    stop_sequences: list[str] = Field(default_factory=list)

    stream: bool = False

    tools: list[ToolDefinition] = Field(default_factory=list)

    output_schema: dict[str, Any] | None = None

    conversation_id: UUID | None = None

    session_id: UUID | None = None

    request_id: UUID = Field(default_factory=uuid4)

    metadata: dict[str, Any] = Field(default_factory=dict)


class ProviderCapabilities(
    BaseModel,
):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    streaming: bool = True

    structured_output: bool = False

    tool_calling: bool = False

    reasoning: bool = False

    vision: bool = False

    json_mode: bool = False

    citations: bool = False

    thinking_tokens: bool = False

    parallel_tool_calls: bool = False

    multimodal_input: bool = False

    multimodal_output: bool = False


class StreamChunk(BaseModel):
    event: StreamEventType

    content: str | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)


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
    reasoning_tokens: int = 0

    cached_tokens: int = 0

    total_tokens: int = 0

    estimated_cost_usd: float = 0

    cache_hit: bool = False
    retries: int = 0

    streamed: bool = False


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
    parsed_output: Any | None = None

    tool_calls: list[Any] = Field(default_factory=list)

    citations: list[Any] = Field(default_factory=list)

    reasoning: str | None = None

    raw_response: dict[str, Any] | None = None
