from __future__ import annotations

from app.ai.runtime.generation.config import (
    ProviderCapabilities,
)
from app.ai.runtime.generation.enums import (
    GenerationProvider,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class ModelMetadata(
    BaseModel,
):
    """
    Canonical model metadata.

    Used by:

    - Routing
    - Benchmarking
    - Cost estimation
    - Provider selection

    Costs and scores are best-effort estimates and should periodically
    be refreshed from provider pricing pages and evaluation results.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    provider: GenerationProvider

    model_name: str

    display_name: str

    context_window: int

    capabilities: ProviderCapabilities

    cost_per_input_1m: float = Field(
        default=0,
        ge=0,
    )

    cost_per_output_1m: float = Field(
        default=0,
        ge=0,
    )

    average_latency_ms: int | None = Field(
        default=None,
        ge=0,
    )

    #
    # Task scores (0-1). Routing scores candidates against these rather
    # than against a hardcoded model name, so a strategy asks "who has
    # the best planning score" instead of "give me Claude" — see
    # `routing/scoring`.
    #

    quality_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    reasoning_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    coding_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    summarization_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    classification_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    extraction_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    planning_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    review_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    speed_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    reliability_score: float = Field(
        default=0.5,
        ge=0,
        le=1,
    )

    #
    # Policy flags.
    #

    priority: int = Field(
        default=100,
        description="Tie-breaker when scores are equal. Lower ranks higher.",
    )

    enabled: bool = True
    """
    Hard kill-switch. `False` removes a model from routing entirely,
    with no request-level override — for retired or broken entries.
    Distinct from `experimental`/`local`, which are soft, opt-in gates.
    """

    experimental: bool = False

    local: bool = False


GPT_5 = ModelMetadata(
    provider=GenerationProvider.OPENAI,
    model_name="gpt-5",
    display_name="GPT-5",
    context_window=400_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    ),
    cost_per_input_1m=1.25,
    cost_per_output_1m=10.0,
    average_latency_ms=3500,
    quality_score=0.95,
    reasoning_score=0.93,
    coding_score=0.95,
    summarization_score=0.75,
    classification_score=0.80,
    extraction_score=0.85,
    planning_score=0.85,
    review_score=0.92,
    speed_score=0.55,
    reliability_score=0.92,
    priority=10,
)

GPT_5_MINI = ModelMetadata(
    provider=GenerationProvider.OPENAI,
    model_name="gpt-5-mini",
    display_name="GPT-5 Mini",
    context_window=400_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    ),
    cost_per_input_1m=0.25,
    cost_per_output_1m=2.0,
    average_latency_ms=1500,
    quality_score=0.80,
    reasoning_score=0.72,
    coding_score=0.70,
    summarization_score=0.88,
    classification_score=0.85,
    extraction_score=0.88,
    planning_score=0.65,
    review_score=0.72,
    speed_score=0.80,
    reliability_score=0.88,
    priority=30,
)

GPT_5_NANO = ModelMetadata(
    provider=GenerationProvider.OPENAI,
    model_name="gpt-5-nano",
    display_name="GPT-5 Nano",
    context_window=400_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=False,
        vision=False,
        json_mode=True,
    ),
    cost_per_input_1m=0.05,
    cost_per_output_1m=0.40,
    average_latency_ms=600,
    quality_score=0.60,
    reasoning_score=0.45,
    coding_score=0.40,
    summarization_score=0.65,
    classification_score=0.85,
    extraction_score=0.70,
    planning_score=0.35,
    review_score=0.45,
    speed_score=0.95,
    reliability_score=0.85,
    priority=50,
)

CLAUDE_SONNET_4 = ModelMetadata(
    provider=GenerationProvider.CLAUDE,
    model_name="claude-sonnet-5",
    display_name="Claude Sonnet 5",
    context_window=200_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    ),
    cost_per_input_1m=3.0,
    cost_per_output_1m=15.0,
    average_latency_ms=2800,
    quality_score=0.93,
    reasoning_score=0.90,
    coding_score=0.87,
    summarization_score=0.85,
    classification_score=0.75,
    extraction_score=0.80,
    planning_score=0.98,
    review_score=0.97,
    speed_score=0.65,
    reliability_score=0.94,
    priority=5,
)

CLAUDE_OPUS_4 = ModelMetadata(
    provider=GenerationProvider.CLAUDE,
    model_name="claude-opus-4",
    display_name="Claude Opus 4",
    context_window=200_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    ),
    cost_per_input_1m=15.0,
    cost_per_output_1m=75.0,
    average_latency_ms=5000,
    quality_score=0.98,
    reasoning_score=0.97,
    coding_score=0.90,
    summarization_score=0.85,
    classification_score=0.78,
    extraction_score=0.83,
    planning_score=0.80,
    review_score=0.78,
    speed_score=0.40,
    reliability_score=0.95,
    priority=15,
)

GEMINI_2_5_PRO = ModelMetadata(
    provider=GenerationProvider.GEMINI,
    model_name="gemini-2.5-pro",
    display_name="Gemini 2.5 Pro",
    context_window=1_000_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    ),
    cost_per_input_1m=1.25,
    cost_per_output_1m=10.0,
    average_latency_ms=2500,
    quality_score=0.90,
    reasoning_score=0.86,
    coding_score=0.82,
    summarization_score=0.85,
    classification_score=0.75,
    extraction_score=0.82,
    planning_score=0.78,
    review_score=0.80,
    speed_score=0.60,
    reliability_score=0.88,
    priority=20,
)
GEMINI_2_5_FLASH = ModelMetadata(
    provider=GenerationProvider.GEMINI,
    model_name="gemini-2.5-flash",
    display_name="Gemini 2.5 Flash",
    context_window=1_000_000,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    ),
    cost_per_input_1m=0.30,
    cost_per_output_1m=2.50,
    average_latency_ms=900,
    quality_score=0.78,
    reasoning_score=0.68,
    coding_score=0.62,
    summarization_score=0.90,
    classification_score=0.80,
    extraction_score=0.80,
    planning_score=0.60,
    review_score=0.65,
    speed_score=0.90,
    reliability_score=0.85,
    priority=25,
)

LLAMA_3_3_70B = ModelMetadata(
    provider=GenerationProvider.GROQ,
    model_name="llama-3.3-70b-versatile",
    display_name="Llama 3.3 70B",
    context_window=131_072,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=False,
        vision=False,
        json_mode=True,
    ),
    cost_per_input_1m=0.59,
    cost_per_output_1m=0.79,
    average_latency_ms=350,
    quality_score=0.65,
    reasoning_score=0.55,
    coding_score=0.55,
    summarization_score=0.70,
    classification_score=0.70,
    extraction_score=0.65,
    planning_score=0.45,
    review_score=0.50,
    speed_score=0.97,
    reliability_score=0.80,
    priority=60,
)

DEEPSEEK_R1_DISTILL_70B = ModelMetadata(
    provider=GenerationProvider.GROQ,
    model_name="deepseek-r1-distill-llama-70b",
    display_name="DeepSeek R1 Distill 70B",
    context_window=131_072,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=True,
        vision=False,
        json_mode=True,
    ),
    cost_per_input_1m=0.75,
    cost_per_output_1m=0.99,
    average_latency_ms=500,
    quality_score=0.72,
    reasoning_score=0.80,
    coding_score=0.68,
    summarization_score=0.60,
    classification_score=0.60,
    extraction_score=0.60,
    planning_score=0.60,
    review_score=0.60,
    speed_score=0.90,
    reliability_score=0.75,
    priority=55,
)

QWEN3 = ModelMetadata(
    provider=GenerationProvider.OLLAMA,
    model_name="qwen3:latest",
    display_name="Qwen 3",
    context_window=32_768,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=True,
        vision=False,
        json_mode=True,
    ),
    average_latency_ms=None,
    quality_score=0.65,
    reasoning_score=0.62,
    coding_score=0.58,
    summarization_score=0.60,
    classification_score=0.55,
    extraction_score=0.55,
    planning_score=0.50,
    review_score=0.50,
    speed_score=0.50,
    reliability_score=0.60,
    priority=90,
    experimental=True,
    local=True,
)

DEEPSEEK_R1 = ModelMetadata(
    provider=GenerationProvider.OLLAMA,
    model_name="deepseek-r1",
    display_name="DeepSeek R1",
    context_window=32_768,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=True,
        vision=False,
        json_mode=True,
    ),
    average_latency_ms=None,
    quality_score=0.68,
    reasoning_score=0.75,
    coding_score=0.60,
    summarization_score=0.55,
    classification_score=0.50,
    extraction_score=0.50,
    planning_score=0.55,
    review_score=0.55,
    speed_score=0.45,
    reliability_score=0.55,
    priority=91,
    experimental=True,
    local=True,
)

PHI4 = ModelMetadata(
    provider=GenerationProvider.OLLAMA,
    model_name="phi4",
    display_name="Phi 4",
    context_window=16_384,
    capabilities=ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=False,
        vision=False,
        json_mode=True,
    ),
    average_latency_ms=None,
    quality_score=0.55,
    reasoning_score=0.48,
    coding_score=0.45,
    summarization_score=0.55,
    classification_score=0.55,
    extraction_score=0.50,
    planning_score=0.35,
    review_score=0.40,
    speed_score=0.60,
    reliability_score=0.55,
    priority=92,
    experimental=True,
    local=True,
)

ALL_MODELS: list[ModelMetadata] = [
    GPT_5,
    GPT_5_MINI,
    GPT_5_NANO,
    CLAUDE_SONNET_4,
    CLAUDE_OPUS_4,
    GEMINI_2_5_PRO,
    GEMINI_2_5_FLASH,
    LLAMA_3_3_70B,
    DEEPSEEK_R1_DISTILL_70B,
    QWEN3,
    DEEPSEEK_R1,
    PHI4,
]
MODELS_BY_PROVIDER: dict[
    GenerationProvider,
    list[ModelMetadata],
] = {}
for model in ALL_MODELS:
    MODELS_BY_PROVIDER.setdefault(
        model.provider,
        [],
    ).append(model)
