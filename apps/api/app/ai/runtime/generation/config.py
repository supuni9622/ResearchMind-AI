from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class BaseGenerationConfig(
    BaseModel,
):
    """
    Shared configuration
    for all generation providers.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
    )

    timeout_seconds: int = Field(
        default=120,
        ge=1,
    )

    max_retries: int = Field(
        default=2,
        ge=0,
    )

    enable_cache: bool = True

    enable_streaming: bool = True


class ProviderCapabilities(
    BaseModel,
):
    """
    Provider capabilities.

    Used by:

    - Routing
    - Structured Outputs
    - Agent Runtime
    - Benchmarks
    - Observability
    """

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


class OpenAIGenerationConfig(
    BaseGenerationConfig,
):
    model_name: str = "gpt-5"

    temperature: float = 0.1

    max_tokens: int = 4000

    context_window: int = 400_000

    capabilities: ProviderCapabilities = ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    )
    cost_per_input_1m: float

    cost_per_output_1m: float


class ClaudeGenerationConfig(
    BaseGenerationConfig,
):
    model_name: str = "claude-sonnet-4"

    temperature: float = 0.1

    max_tokens: int = 4000

    context_window: int = 200_000

    capabilities: ProviderCapabilities = ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    )
    cost_per_input_1m: float

    cost_per_output_1m: float


class GeminiGenerationConfig(
    BaseGenerationConfig,
):
    model_name: str = "gemini-2.5-pro"

    temperature: float = 0.1

    max_tokens: int = 8000

    context_window: int = 1_000_000

    capabilities: ProviderCapabilities = ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=True,
        reasoning=True,
        vision=True,
        json_mode=True,
    )
    cost_per_input_1m: float

    cost_per_output_1m: float


class GroqGenerationConfig(
    BaseGenerationConfig,
):
    model_name: str = "llama-3.3-70b-versatile"

    temperature: float = 0.1

    max_tokens: int = 4000

    context_window: int = 131_072

    capabilities: ProviderCapabilities = ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=False,
        vision=False,
        json_mode=True,
    )
    cost_per_input_1m: float

    cost_per_output_1m: float


class OllamaGenerationConfig(
    BaseGenerationConfig,
):
    host: str = "http://localhost:11434"

    model_name: str = "qwen3:latest"

    temperature: float = 0.1

    max_tokens: int = 4000

    context_window: int = 32_768

    capabilities: ProviderCapabilities = ProviderCapabilities(
        streaming=True,
        structured_output=True,
        tool_calling=False,
        reasoning=False,
        vision=False,
        json_mode=True,
    )
    cost_per_input_1m: float

    cost_per_output_1m: float
