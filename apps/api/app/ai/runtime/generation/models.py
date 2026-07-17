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
from app.ai.runtime.generation.routing.enums import (
    RequiredCapability,
    RoutingStrategy,
)
from app.ai.runtime.generation.validation.models import (
    ValidationReport,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
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

    max_regeneration_attempts: int = Field(
        default=1,
        ge=0,
    )
    """
    Opt-in retry-on-invalid-output budget (default 0 — no regeneration,
    matches prior behavior for every existing caller).

    When >0, `GenerationService.generate()` re-calls the provider (with a
    corrective instruction appended describing what was wrong) up to this
    many extra times if the initial attempt's `parsed_output` is `None`
    (parsing failed) or `ValidationReport.output_validation.valid` is
    `False` (schema mismatch, fabricated citation, ...). See
    `GenerationResult.regeneration_attempts`.
    """

    output_model: type[BaseModel] | None = None
    """
    Convenience alternative to `output_schema`.

    When set and `output_schema` is not explicitly provided, the JSON
    Schema is derived from this model via `model_json_schema()`. After
    generation, `GenerationResult.parsed_output` is validated back into
    an instance of this model (see `GenerationService.generate`).

    For strict schema compliance across providers (OpenAI, Groq), the
    model should set `model_config = ConfigDict(extra="forbid")` so the
    generated schema includes `additionalProperties: false`.
    """

    conversation_id: UUID | None = None

    session_id: UUID | None = None

    request_id: UUID = Field(default_factory=uuid4)

    metadata: dict[str, Any] = Field(default_factory=dict)

    routing_strategy: RoutingStrategy | None = None
    """
    When `GenerationService.generate()` is called without an explicit
    `provider`, this picks which routing strategy resolves the model —
    see `routing/`. Defaults to `RoutingStrategy.AUTO` if left unset.
    Ignored when `provider` is given explicitly.
    """

    required_capabilities: list[RequiredCapability] = Field(default_factory=list)
    """
    Capabilities the routed model must support (e.g. tool calling).
    Only consulted alongside `routing_strategy` — has no effect when
    `provider` is given explicitly.
    """

    @model_validator(mode="after")
    def _derive_output_schema_from_model(self) -> GenerationRequest:

        if self.output_schema is None and self.output_model is not None:
            self.output_schema = self.output_model.model_json_schema()

        return self


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

    validation: ValidationReport | None = None
    """
    Populated by `GenerationService.generate()` via `ValidationService`
    (see `generation/validation/`) — input, output, and hallucination
    stage checks. `None` when no `ValidationService` was wired into
    `GenerationService` (see `generation/create.py`).
    """

    regeneration_attempts: int = 0
    """
    How many extra provider calls `GenerationService.generate()` made
    beyond the first, retrying with corrective feedback because the
    prior attempt's output failed to parse or failed validation. 0 means
    the first attempt was accepted (or `request.max_regeneration_attempts`
    was 0). This result reflects the *last* attempt made.
    """
