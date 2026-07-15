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

        Costs are best-effort estimates and
    should periodically be updated from
    provider pricing pages.
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
)

CLAUDE_SONNET_4 = ModelMetadata(
    provider=GenerationProvider.CLAUDE,
    model_name="claude-sonnet-4",
    display_name="Claude Sonnet 4",
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
