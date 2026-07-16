"""
Unit tests for GroqProvider.

Covers:
- Provider identifier
- generate() happy path: request shaping, usage extraction, result content
- generate() with a response carrying no usage data
- generate() best-effort JSON parsing for JSON/STRUCTURED response formats
- generate() retries transient failures and eventually raises
  GenerationExecutionError, preserving the original exception as __cause__
- generate() succeeds after a transient failure within the retry budget
- stream() yields START, TOKEN, COMPLETED events and skips choice-less chunks
- stream() wraps SDK failures in GenerationExecutionError
- generate_structured() delegates to generate()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import GroqGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.exceptions import GenerationExecutionError
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.providers.groq import GroqProvider
from app.core.settings import settings
from groq import GroqError


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
    response_format: ResponseFormat = ResponseFormat.TEXT,
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="retrieved context", chunks=[]),
        user_prompt=user_prompt,
        response_format=response_format,
    )


def _make_provider(
    monkeypatch: pytest.MonkeyPatch, **config_overrides
) -> tuple[GroqProvider, MagicMock]:
    """
    Returns the provider plus a directly-typed handle to its mocked SDK
    client. Groq's SDK ships precise type stubs, so mypy resolves
    `provider._client...` back to the real AsyncGroq method signatures
    (which have no `.return_value`/`.side_effect`); configuring and
    asserting against the `client` handle returned here instead keeps
    the test file mypy-clean without weakening what's being verified.
    """

    monkeypatch.setattr(settings, "groq_api_key", "test-groq-key")

    config = GroqGenerationConfig(
        cost_per_input_1m=0.1,
        cost_per_output_1m=0.1,
        **config_overrides,
    )
    provider = GroqProvider(config=config)
    client = MagicMock()
    client.chat.completions.create = AsyncMock()
    provider._client = client
    return provider, client


def _make_completion(
    *,
    content: str = "hello world",
    finish_reason: str = "stop",
    prompt_tokens: int = 10,
    completion_tokens: int = 5,
    total_tokens: int = 15,
    has_usage: bool = True,
) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = content
    response.choices[0].finish_reason = finish_reason
    response.model_dump.return_value = {"id": "chatcmpl-test"}

    if has_usage:
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        response.usage.total_tokens = total_tokens
    else:
        response.usage = None

    return response


def _make_chunk(content: str | None, has_choices: bool = True) -> MagicMock:
    chunk = MagicMock()
    if not has_choices:
        chunk.choices = []
        return chunk
    chunk.choices[0].delta.content = content
    return chunk


def test_provider_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, _ = _make_provider(monkeypatch)

    assert provider.provider == GenerationProvider.GROQ


async def test_generate_returns_result_with_expected_content_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _make_completion()

    result = await provider.generate(_make_request())

    assert result.content == "hello world"
    assert result.finish_reason == "stop"
    assert result.provider == GenerationProvider.GROQ
    assert result.statistics.prompt_tokens == 10
    assert result.statistics.completion_tokens == 5
    assert result.statistics.total_tokens == 15
    assert result.raw_response == {"id": "chatcmpl-test"}


async def test_generate_calls_client_with_expected_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _make_completion()

    request = _make_request(user_prompt="what is the capital of France?")

    await provider.generate(request)

    _, kwargs = client.chat.completions.create.call_args
    assert kwargs["model"] == provider.config.model_name
    assert kwargs["temperature"] == provider.config.temperature
    assert kwargs["max_completion_tokens"] == provider.config.max_tokens
    assert any(
        "what is the capital of France?" in message["content"] for message in kwargs["messages"]
    )


async def test_generate_handles_missing_usage_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _make_completion(has_usage=False)

    result = await provider.generate(_make_request())

    assert result.statistics.prompt_tokens == 0
    assert result.statistics.completion_tokens == 0
    assert result.statistics.total_tokens == 0


async def test_generate_parses_json_when_response_format_is_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _make_completion(
        content='{"answer": 42}',
    )

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output == {"answer": 42}


async def test_generate_leaves_parsed_output_none_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _make_completion(
        content="not valid json",
    )

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output is None


async def test_generate_retries_then_raises_execution_error_on_persistent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    provider, client = _make_provider(monkeypatch, max_retries=2)
    client.chat.completions.create.side_effect = GroqError("rate limited")

    with pytest.raises(GenerationExecutionError) as exc_info:
        await provider.generate(_make_request())

    assert isinstance(exc_info.value.__cause__, GroqError)
    assert client.chat.completions.create.await_count == 3


async def test_generate_succeeds_after_transient_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch, max_retries=2)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    client.chat.completions.create.side_effect = [
        GroqError("transient"),
        _make_completion(content="recovered"),
    ]

    result = await provider.generate(_make_request())

    assert result.content == "recovered"
    assert client.chat.completions.create.await_count == 2


async def test_stream_yields_start_token_and_completed_events_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _AsyncIter(
        [
            _make_chunk("Hello"),
            _make_chunk(None, has_choices=False),
            _make_chunk(" world"),
            _make_chunk(None),
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
    client.chat.completions.create.side_effect = GroqError("auth failed")

    with pytest.raises(GenerationExecutionError) as exc_info:
        async for _ in provider.stream(_make_request()):
            pass

    assert isinstance(exc_info.value.__cause__, GroqError)


async def test_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.chat.completions.create.return_value = _make_completion(
        content='{"ok": true}',
    )

    result = await provider.generate_structured(
        _make_request(response_format=ResponseFormat.STRUCTURED)
    )

    assert result.parsed_output == {"ok": True}
