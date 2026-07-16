"""
Unit tests for OpenAIProvider.

Covers:
- Provider identifier
- generate() happy path against the Responses API shape (output_text, usage.*)
- generate() omits temperature/max_output_tokens when unset on the request
- generate() with a response carrying no usage data
- generate() best-effort JSON parsing gated on request.output_schema
  (NOT response_format, unlike the chat-completions style providers)
- generate() retries transient failures and eventually raises
  GenerationExecutionError, preserving the original exception as __cause__
- stream() yields START, TOKEN, COMPLETED and ignores non-delta events
- stream() wraps SDK failures in GenerationExecutionError
- generate_structured() delegates to generate()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import OpenAIGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.exceptions import GenerationExecutionError
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.providers.openai import OpenAIProvider
from app.core.settings import settings
from openai import OpenAIError


class _AsyncIter:
    """Minimal async-iterable test double for SDK streaming responses."""

    def __init__(self, items: list) -> None:
        self._items = iter(items)

    def __aiter__(self) -> _AsyncIter:
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration from None


def _make_request(
    user_prompt: str = "hello",
    output_schema: dict | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="retrieved context", chunks=[]),
        user_prompt=user_prompt,
        output_schema=output_schema,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _make_provider(
    monkeypatch: pytest.MonkeyPatch, **config_overrides
) -> tuple[OpenAIProvider, MagicMock]:
    """
    Returns the provider plus a directly-typed handle to its mocked SDK
    client. OpenAI's SDK ships precise type stubs, so mypy resolves
    `provider._client...` back to the real AsyncOpenAI method signatures
    (which have no `.return_value`/`.side_effect`); configuring and
    asserting against the `client` handle returned here instead keeps
    the test file mypy-clean without weakening what's being verified.
    """

    monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")

    config = OpenAIGenerationConfig(
        cost_per_input_1m=0.1,
        cost_per_output_1m=0.1,
        **config_overrides,
    )
    provider = OpenAIProvider(config=config)
    client = MagicMock()
    client.responses.create = AsyncMock()
    provider._client = client
    return provider, client


def _make_response(
    *,
    output_text: str = "hello world",
    input_tokens: int = 10,
    output_tokens: int = 5,
    total_tokens: int = 15,
    reasoning_tokens: int = 0,
    cached_tokens: int = 0,
    has_usage: bool = True,
) -> MagicMock:
    response = MagicMock()
    response.output_text = output_text
    response.model_dump.return_value = {"id": "resp-test"}

    if has_usage:
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
        response.usage.total_tokens = total_tokens
        response.usage.reasoning_tokens = reasoning_tokens
        response.usage.cached_tokens = cached_tokens
    else:
        response.usage = None

    return response


def _make_event(event_type: str, delta: str | None = None) -> MagicMock:
    event = MagicMock()
    event.type = event_type
    event.delta = delta
    return event


def test_provider_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, _ = _make_provider(monkeypatch)

    assert provider.provider == GenerationProvider.OPENAI


async def test_generate_returns_result_with_expected_content_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response()

    result = await provider.generate(_make_request())

    assert result.content == "hello world"
    assert result.provider == GenerationProvider.OPENAI
    assert result.statistics.prompt_tokens == 10
    assert result.statistics.completion_tokens == 5
    assert result.statistics.total_tokens == 15
    assert result.raw_response == {"id": "resp-test"}


async def test_generate_omits_temperature_and_max_tokens_when_unset_on_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response()

    await provider.generate(_make_request())

    _, kwargs = client.responses.create.call_args
    assert "temperature" not in kwargs
    assert "max_output_tokens" not in kwargs


async def test_generate_passes_temperature_and_max_tokens_when_set_on_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response()

    await provider.generate(_make_request(temperature=0.7, max_tokens=256))

    _, kwargs = client.responses.create.call_args
    assert kwargs["temperature"] == 0.7
    assert kwargs["max_output_tokens"] == 256


async def test_generate_handles_missing_usage_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response(has_usage=False)

    result = await provider.generate(_make_request())

    assert result.statistics.prompt_tokens == 0
    assert result.statistics.completion_tokens == 0
    assert result.statistics.total_tokens == 0


async def test_generate_parses_json_when_output_schema_is_set(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response(
        output_text='{"answer": 42}',
    )

    result = await provider.generate(_make_request(output_schema={"type": "object"}))

    assert result.parsed_output == {"answer": 42}


async def test_generate_skips_json_parsing_when_output_schema_is_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response(
        output_text='{"answer": 42}',
    )

    result = await provider.generate(_make_request())

    assert result.parsed_output is None


async def test_generate_leaves_parsed_output_none_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response(
        output_text="not valid json",
    )

    result = await provider.generate(_make_request(output_schema={"type": "object"}))

    assert result.parsed_output is None


async def test_generate_retries_then_raises_execution_error_on_persistent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    provider, client = _make_provider(monkeypatch, max_retries=1)
    client.responses.create.side_effect = OpenAIError("rate limited")

    with pytest.raises(GenerationExecutionError) as exc_info:
        await provider.generate(_make_request())

    assert isinstance(exc_info.value.__cause__, OpenAIError)
    assert client.responses.create.await_count == 2


async def test_stream_yields_start_token_and_completed_events_and_ignores_other_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _AsyncIter(
        [
            _make_event("response.created"),
            _make_event("response.output_text.delta", delta="Hello"),
            _make_event("response.output_text.delta", delta=" world"),
            _make_event("response.completed"),
        ]
    )

    events = [chunk async for chunk in provider.stream(_make_request())]

    assert [event.event for event in events] == [
        StreamEventType.START,
        StreamEventType.TOKEN,
        StreamEventType.TOKEN,
        StreamEventType.COMPLETED,
    ]
    assert [event.content for event in events if event.event == StreamEventType.TOKEN] == [
        "Hello",
        " world",
    ]


async def test_stream_raises_execution_error_on_sdk_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.side_effect = OpenAIError("auth failed")

    with pytest.raises(GenerationExecutionError) as exc_info:
        async for _ in provider.stream(_make_request()):
            pass

    assert isinstance(exc_info.value.__cause__, OpenAIError)


async def test_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.responses.create.return_value = _make_response(
        output_text='{"ok": true}',
    )

    result = await provider.generate_structured(_make_request(output_schema={"type": "object"}))

    assert result.parsed_output == {"ok": True}
