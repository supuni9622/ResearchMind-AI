"""
Cross-provider structured-output contract tests.

Per-provider JSON-parsing outcomes (valid/invalid JSON -> parsed_output)
are covered in test_groq.py / test_openai.py / test_claude.py /
test_gemini.py / test_ollama.py. This file covers the *shared* delegation
contract:

- BaseGenerationProvider.generate_structured() default delegates to
  generate() for providers that don't override it.
- OpenAIProvider doesn't override generate_structured() at all - it gets
  structured-output support purely through inheriting the base default.
- GroqProvider / ClaudeProvider / GeminiProvider / OllamaProvider each
  override generate_structured() with an (identical) explicit delegation
  to generate() - every one of them is a pure passthrough: same request
  in, same GenerationResult out, generate() called exactly once.
- generate_structured() does not change GenerationExecution.operation:
  it stays GENERATE even though a GENERATE_STRUCTURED enum value exists.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import (
    ClaudeGenerationConfig,
    GeminiGenerationConfig,
    GroqGenerationConfig,
    OllamaGenerationConfig,
    OpenAIGenerationConfig,
)
from app.ai.runtime.generation.enums import GenerationOperation, GenerationProvider
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.providers.base import BaseGenerationProvider
from app.ai.runtime.generation.providers.claude import ClaudeProvider
from app.ai.runtime.generation.providers.gemini import GeminiProvider
from app.ai.runtime.generation.providers.groq import GroqProvider
from app.ai.runtime.generation.providers.ollama import OllamaProvider
from app.ai.runtime.generation.providers.openai import OpenAIProvider
from app.core.settings import settings


class _MinimalProvider(BaseGenerationProvider):
    """The smallest possible concrete provider: does not override generate_structured()."""

    @property
    def provider(self) -> GenerationProvider:
        return GenerationProvider.GROQ

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError


def _make_request() -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="retrieved context", chunks=[]),
        user_prompt="hello",
    )


def _make_result(request: GenerationRequest, provider: GenerationProvider) -> GenerationResult:
    return GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(provider=provider, model="test-model"),
        provider=provider,
        model="test-model",
        content="hello world",
    )


async def test_base_generate_structured_default_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _MinimalProvider(
        config=GroqGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    request = _make_request()
    result = _make_result(request, GenerationProvider.GROQ)
    mock_generate = AsyncMock(return_value=result)
    monkeypatch.setattr(provider, "generate", mock_generate)

    returned = await provider.generate_structured(request)

    assert returned is result
    mock_generate.assert_awaited_once_with(request)


async def test_openai_generate_structured_delegates_to_generate_via_inherited_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    provider = OpenAIProvider(
        config=OpenAIGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    request = _make_request()
    result = _make_result(request, GenerationProvider.OPENAI)
    mock_generate = AsyncMock(return_value=result)
    monkeypatch.setattr(provider, "generate", mock_generate)

    returned = await provider.generate_structured(request)

    assert returned is result
    mock_generate.assert_awaited_once_with(request)


async def test_groq_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    provider = GroqProvider(
        config=GroqGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    request = _make_request()
    result = _make_result(request, GenerationProvider.GROQ)
    mock_generate = AsyncMock(return_value=result)
    monkeypatch.setattr(provider, "generate", mock_generate)

    returned = await provider.generate_structured(request)

    assert returned is result
    mock_generate.assert_awaited_once_with(request)


async def test_claude_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    provider = ClaudeProvider(
        config=ClaudeGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    request = _make_request()
    result = _make_result(request, GenerationProvider.CLAUDE)
    mock_generate = AsyncMock(return_value=result)
    monkeypatch.setattr(provider, "generate", mock_generate)

    returned = await provider.generate_structured(request)

    assert returned is result
    mock_generate.assert_awaited_once_with(request)


async def test_gemini_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")
    provider = GeminiProvider(
        config=GeminiGenerationConfig(cost_per_input_1m=0.1, cost_per_output_1m=0.1)
    )
    request = _make_request()
    result = _make_result(request, GenerationProvider.GEMINI)
    mock_generate = AsyncMock(return_value=result)
    monkeypatch.setattr(provider, "generate", mock_generate)

    returned = await provider.generate_structured(request)

    assert returned is result
    mock_generate.assert_awaited_once_with(request)


async def test_ollama_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = OllamaProvider(config=OllamaGenerationConfig())
    request = _make_request()
    result = _make_result(request, GenerationProvider.OLLAMA)
    mock_generate = AsyncMock(return_value=result)
    monkeypatch.setattr(provider, "generate", mock_generate)

    returned = await provider.generate_structured(request)

    assert returned is result
    mock_generate.assert_awaited_once_with(request)


async def test_generate_structured_does_not_change_the_execution_operation() -> None:
    """
    GenerationOperation.GENERATE_STRUCTURED exists as an enum value, but
    nothing currently sets it: build_result() always defaults
    GenerationExecution.operation to GENERATE, even when reached via the
    generate_structured() path. This exercises the real generate()
    implementation (SDK client mocked, not provider.generate itself) so
    the assertion reflects build_result()'s actual default rather than a
    pre-built fixture.
    """

    provider = OllamaProvider(config=OllamaGenerationConfig())
    client = MagicMock()
    response = MagicMock()
    response.model_dump.return_value = {}
    response.message.content = "hello world"
    response.prompt_eval_count = 1
    response.eval_count = 1
    client.chat = AsyncMock(return_value=response)
    provider._client = client

    returned = await provider.generate_structured(_make_request())

    assert returned.execution.operation == GenerationOperation.GENERATE
