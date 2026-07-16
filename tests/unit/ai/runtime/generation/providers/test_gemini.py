"""
Unit tests for GeminiProvider.

Covers:
- Provider identifier
- generate() happy path: usage_metadata extraction (including
  thoughts_token_count as reasoning_tokens), content from response.text
- generate() with a response carrying no usage_metadata
- generate() best-effort JSON parsing for JSON/STRUCTURED response formats
- generate() retries transient failures and eventually raises
  GenerationExecutionError, preserving the original exception as __cause__
- stream() yields START, TOKEN, COMPLETED and skips empty-text chunks
- stream() wraps SDK failures in GenerationExecutionError
- health_check() returns True on success and False (without raising) on
  SDK failure
- generate_structured() delegates to generate()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import GeminiGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.exceptions import GenerationExecutionError
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.providers.gemini import GeminiProvider
from app.core.settings import settings
from google.genai.errors import APIError


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


def _make_api_error(message: str) -> APIError:
    return APIError(500, {"error": {"message": message, "status": "INTERNAL"}})


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
) -> tuple[GeminiProvider, MagicMock]:
    """
    Returns the provider plus a directly-typed handle to its mocked SDK
    client. google-genai ships precise type stubs, so mypy resolves
    `provider._client...` back to the real Client method signatures
    (which have no `.return_value`/`.side_effect`); configuring and
    asserting against the `client` handle returned here instead keeps
    the test file mypy-clean without weakening what's being verified.
    """

    monkeypatch.setattr(settings, "gemini_api_key", "test-gemini-key")

    config = GeminiGenerationConfig(
        cost_per_input_1m=0.1,
        cost_per_output_1m=0.1,
        **config_overrides,
    )
    provider = GeminiProvider(config=config)
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock()
    client.aio.models.generate_content_stream = AsyncMock()
    provider._client = client
    return provider, client


def _make_response(
    *,
    text: str = "hello world",
    prompt_token_count: int = 10,
    candidates_token_count: int = 5,
    total_token_count: int = 15,
    thoughts_token_count: int = 0,
    has_usage: bool = True,
) -> MagicMock:
    response = MagicMock()
    response.text = text
    response.model_dump.return_value = {"id": "gemini-test"}

    if has_usage:
        response.usage_metadata.prompt_token_count = prompt_token_count
        response.usage_metadata.candidates_token_count = candidates_token_count
        response.usage_metadata.total_token_count = total_token_count
        response.usage_metadata.thoughts_token_count = thoughts_token_count
    else:
        response.usage_metadata = None

    return response


def _make_chunk(text: str | None) -> MagicMock:
    chunk = MagicMock()
    chunk.text = text
    return chunk


def test_provider_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, _ = _make_provider(monkeypatch)

    assert provider.provider == GenerationProvider.GEMINI


async def test_generate_returns_result_with_expected_content_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response()

    result = await provider.generate(_make_request())

    assert result.content == "hello world"
    assert result.provider == GenerationProvider.GEMINI
    assert result.statistics.prompt_tokens == 10
    assert result.statistics.completion_tokens == 5
    assert result.statistics.total_tokens == 15
    assert result.raw_response == {"id": "gemini-test"}


async def test_generate_includes_thoughts_token_count_as_reasoning_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response(
        prompt_token_count=10,
        candidates_token_count=5,
        thoughts_token_count=3,
        total_token_count=18,
    )

    result = await provider.generate(_make_request())

    assert result.statistics.reasoning_tokens == 3
    assert result.statistics.total_tokens == 18


async def test_generate_handles_missing_usage_metadata_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response(has_usage=False)

    result = await provider.generate(_make_request())

    assert result.statistics.prompt_tokens == 0
    assert result.statistics.completion_tokens == 0
    assert result.statistics.total_tokens == 0


async def test_generate_parses_json_when_response_format_is_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response(
        text='{"answer": 42}',
    )

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output == {"answer": 42}


async def test_generate_leaves_parsed_output_none_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response(
        text="not valid json",
    )

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output is None


async def test_generate_retries_then_raises_execution_error_on_persistent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    provider, client = _make_provider(monkeypatch, max_retries=1)
    client.aio.models.generate_content.side_effect = _make_api_error("overloaded")

    with pytest.raises(GenerationExecutionError) as exc_info:
        await provider.generate(_make_request())

    assert isinstance(exc_info.value.__cause__, APIError)
    assert client.aio.models.generate_content.await_count == 2


async def test_stream_yields_start_token_and_completed_events_and_skips_empty_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content_stream.return_value = _AsyncIter(
        [
            _make_chunk("Hello"),
            _make_chunk(None),
            _make_chunk(""),
            _make_chunk(" world"),
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
    client.aio.models.generate_content_stream.side_effect = _make_api_error("auth failed")

    with pytest.raises(GenerationExecutionError) as exc_info:
        async for _ in provider.stream(_make_request()):
            pass

    assert isinstance(exc_info.value.__cause__, APIError)


async def test_health_check_returns_true_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response()

    assert await provider.health_check() is True


async def test_health_check_returns_false_without_raising_on_sdk_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.side_effect = _make_api_error("down")

    assert await provider.health_check() is False


async def test_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.aio.models.generate_content.return_value = _make_response(
        text='{"ok": true}',
    )

    result = await provider.generate_structured(
        _make_request(response_format=ResponseFormat.STRUCTURED)
    )

    assert result.parsed_output == {"ok": True}
