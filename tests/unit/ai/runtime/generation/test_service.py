"""
Unit tests for GenerationService.

Covers:
- Successful delegation to the resolved provider
- Validation failure for an empty user prompt
- Validation failure for empty prompt context
- Provider resolution failure propagates from the registry
- GenerationError subclasses raised by a provider propagate unchanged
- Unexpected (non-domain) exceptions raised by a provider are wrapped in
  GenerationExecutionError
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.exceptions import (
    GenerationExecutionError,
    GenerationProviderNotFoundError,
    GenerationValidationError,
    GuardrailViolationError,
)
from app.ai.runtime.generation.models import (
    GenerationExecution,
    GenerationRequest,
    GenerationResult,
    GenerationStatistics,
)
from app.ai.runtime.generation.registry import GenerationRegistry
from app.ai.runtime.generation.service import GenerationService


def _make_context(text: str = "some retrieved context") -> PromptContext:
    return PromptContext(context=text, chunks=[])


def _make_request(
    user_prompt: str = "hello",
    context: str = "some retrieved context",
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=_make_context(context),
        user_prompt=user_prompt,
    )


def _make_result(request: GenerationRequest) -> GenerationResult:
    return GenerationResult(
        request=request,
        execution=GenerationExecution(),
        statistics=GenerationStatistics(
            provider=GenerationProvider.GROQ,
            model="test-model",
        ),
        provider=GenerationProvider.GROQ,
        model="test-model",
        content="hello world",
    )


def _make_provider(provider: GenerationProvider = GenerationProvider.GROQ) -> AsyncMock:
    fake = AsyncMock()
    fake.provider = provider
    return fake


async def test_generate_delegates_to_the_resolved_provider() -> None:
    request = _make_request()
    result = _make_result(request)

    provider = _make_provider()
    provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    returned = await service.generate(provider=GenerationProvider.GROQ, request=request)

    assert returned is result
    provider.generate.assert_awaited_once_with(request)


async def test_generate_raises_validation_error_for_empty_user_prompt() -> None:
    provider = _make_provider()
    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    request = _make_request(user_prompt="   ")

    with pytest.raises(GenerationValidationError, match="empty"):
        await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_not_awaited()


async def test_generate_raises_validation_error_for_empty_prompt_context() -> None:
    provider = _make_provider()
    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    request = _make_request(context="")

    with pytest.raises(GenerationValidationError, match="context"):
        await service.generate(provider=GenerationProvider.GROQ, request=request)

    provider.generate.assert_not_awaited()


async def test_generate_raises_provider_not_found_error_when_unregistered() -> None:
    service = GenerationService(registry=GenerationRegistry(providers=[]))

    with pytest.raises(GenerationProviderNotFoundError):
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())


async def test_generate_propagates_generation_error_subclasses_unchanged() -> None:
    provider = _make_provider()
    provider.generate = AsyncMock(side_effect=GuardrailViolationError("blocked"))

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    with pytest.raises(GuardrailViolationError, match="blocked"):
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())


async def test_generate_wraps_unexpected_exceptions_in_execution_error() -> None:
    provider = _make_provider()
    provider.generate = AsyncMock(side_effect=RuntimeError("sdk exploded"))

    registry = GenerationRegistry(providers=[provider])
    service = GenerationService(registry=registry)

    with pytest.raises(GenerationExecutionError) as exc_info:
        await service.generate(provider=GenerationProvider.GROQ, request=_make_request())

    assert isinstance(exc_info.value.__cause__, RuntimeError)
    assert str(exc_info.value.__cause__) == "sdk exploded"


async def test_generate_id_uses_the_provider_argument_not_the_result_provider() -> None:
    """
    The service resolves the provider from the registry using the
    `provider` argument; a mismatched `GenerationResult.provider` on the
    returned object should not affect which provider is looked up.
    """

    request = _make_request()
    result = _make_result(request)

    groq_provider = _make_provider(GenerationProvider.GROQ)
    groq_provider.generate = AsyncMock(return_value=result)

    other_provider = _make_provider(GenerationProvider.OPENAI)
    other_provider.generate = AsyncMock(return_value=result)

    registry = GenerationRegistry(providers=[groq_provider, other_provider])
    service = GenerationService(registry=registry)

    await service.generate(provider=GenerationProvider.OPENAI, request=request)

    other_provider.generate.assert_awaited_once()
    groq_provider.generate.assert_not_awaited()
