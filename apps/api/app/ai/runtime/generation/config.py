from __future__ import annotations

from app.ai.runtime.generation.models import (
    ProviderCapabilities,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

__all__ = [
    "BaseGenerationConfig",
    "ClaudeGenerationConfig",
    "GeminiGenerationConfig",
    "GroqGenerationConfig",
    "OllamaGenerationConfig",
    "OpenAIGenerationConfig",
    "ProviderCapabilities",
]


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

    model_name: str

    temperature: float = 0.1

    max_tokens: int = 4000

    context_window: int

    capabilities: ProviderCapabilities = ProviderCapabilities()

    cost_per_input_1m: float

    cost_per_output_1m: float

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
        citations=False,
        thinking_tokens=False,
        parallel_tool_calls=False,
        multimodal_input=False,
        multimodal_output=False,
    )
    cost_per_input_1m: float

    cost_per_output_1m: float


class ClaudeGenerationConfig(
    BaseGenerationConfig,
):
    model_name: str = "claude-sonnet-5"

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
        citations=False,
        thinking_tokens=False,
        parallel_tool_calls=False,
        multimodal_input=False,
        multimodal_output=False,
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
        citations=False,
        thinking_tokens=False,
        parallel_tool_calls=False,
        multimodal_input=False,
        multimodal_output=False,
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
        citations=False,
        thinking_tokens=False,
        parallel_tool_calls=False,
        multimodal_input=False,
        multimodal_output=False,
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
        citations=False,
        thinking_tokens=False,
        parallel_tool_calls=False,
        multimodal_input=False,
        multimodal_output=False,
    )
    cost_per_input_1m: float = 0

    cost_per_output_1m: float = 0
