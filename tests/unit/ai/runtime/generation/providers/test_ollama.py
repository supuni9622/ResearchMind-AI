"""
Unit tests for OllamaProvider.

Covers:
- Provider identifier
- generate() happy path: prompt_eval_count/eval_count usage extraction
  (no nested usage object, unlike the other providers)
- generate() when response.message is falsy, content falls back to ""
- generate() best-effort JSON parsing for JSON/STRUCTURED response formats
- generate() retries transient failures (RequestError/ResponseError/
  ConnectionError) and eventually raises GenerationExecutionError,
  preserving the original exception as __cause__
- stream() yields START, TOKEN, COMPLETED and skips empty-content chunks
- stream() wraps SDK failures in GenerationExecutionError
- health_check() returns True on success and False (without raising) on
  SDK failure
- get_model_metadata() includes installed_models on success and an empty
  list (without raising) on SDK failure
- generate_structured() delegates to generate()
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import OllamaGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.exceptions import GenerationExecutionError
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.providers.ollama import OllamaProvider
from ollama import ResponseError


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


def _make_provider(**config_overrides) -> tuple[OllamaProvider, MagicMock]:
    """
    Returns the provider plus a directly-typed handle to its mocked SDK
    client. Ollama's SDK ships precise type stubs, so mypy resolves
    `provider._client...` back to the real AsyncClient method signatures
    (which have no `.return_value`/`.side_effect`); configuring and
    asserting against the `client` handle returned here instead keeps
    the test file mypy-clean without weakening what's being verified.

    Ollama's client requires no API key, only a host, which has a
    non-empty default (http://localhost:11434) - no settings patch needed.
    """

    config = OllamaGenerationConfig(**config_overrides)
    provider = OllamaProvider(config=config)
    client = MagicMock()
    client.chat = AsyncMock()
    client.ps = AsyncMock()
    client.list = AsyncMock()
    provider._client = client
    return provider, client


def _make_chat_response(
    *,
    content: str | None = "hello world",
    has_message: bool = True,
    prompt_eval_count: int = 10,
    eval_count: int = 5,
) -> MagicMock:
    response = MagicMock()
    response.model_dump.return_value = {"id": "ollama-test"}
    response.prompt_eval_count = prompt_eval_count
    response.eval_count = eval_count

    if has_message:
        response.message.content = content
    else:
        response.message = None

    return response


def _make_chunk(content: str | None, has_message: bool = True) -> MagicMock:
    chunk = MagicMock()
    if not has_message:
        chunk.message = None
        return chunk
    chunk.message.content = content
    return chunk


def test_provider_identifier() -> None:
    provider, _ = _make_provider()

    assert provider.provider == GenerationProvider.OLLAMA


async def test_generate_returns_result_with_expected_content_and_tokens() -> None:
    provider, client = _make_provider()
    client.chat.return_value = _make_chat_response()

    result = await provider.generate(_make_request())

    assert result.content == "hello world"
    assert result.provider == GenerationProvider.OLLAMA
    assert result.statistics.prompt_tokens == 10
    assert result.statistics.completion_tokens == 5
    assert result.statistics.total_tokens == 15
    assert result.raw_response == {"id": "ollama-test"}


async def test_generate_falls_back_to_empty_content_when_message_is_missing() -> None:
    provider, client = _make_provider()
    client.chat.return_value = _make_chat_response(has_message=False)

    result = await provider.generate(_make_request())

    assert result.content == ""


async def test_generate_treats_missing_counts_as_zero() -> None:
    provider, client = _make_provider()
    response = _make_chat_response()
    response.prompt_eval_count = None
    response.eval_count = None
    client.chat.return_value = response

    result = await provider.generate(_make_request())

    assert result.statistics.prompt_tokens == 0
    assert result.statistics.completion_tokens == 0
    assert result.statistics.total_tokens == 0


async def test_generate_parses_json_when_response_format_is_json() -> None:
    provider, client = _make_provider()
    client.chat.return_value = _make_chat_response(content='{"answer": 42}')

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output == {"answer": 42}


async def test_generate_leaves_parsed_output_none_for_invalid_json() -> None:
    provider, client = _make_provider()
    client.chat.return_value = _make_chat_response(content="not valid json")

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output is None


async def test_generate_retries_then_raises_execution_error_on_persistent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    provider, client = _make_provider(max_retries=1)
    client.chat.side_effect = ResponseError("model not found", status_code=404)

    with pytest.raises(GenerationExecutionError) as exc_info:
        await provider.generate(_make_request())

    assert isinstance(exc_info.value.__cause__, ResponseError)
    assert client.chat.await_count == 2


async def test_stream_yields_start_token_and_completed_events_and_skips_empty_chunks() -> None:
    provider, client = _make_provider()
    client.chat.return_value = _AsyncIter(
        [
            _make_chunk("Hello"),
            _make_chunk(None, has_message=False),
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


async def test_stream_raises_execution_error_on_sdk_failure() -> None:
    provider, client = _make_provider()
    client.chat.side_effect = ResponseError("auth failed", status_code=401)

    with pytest.raises(GenerationExecutionError) as exc_info:
        async for _ in provider.stream(_make_request()):
            pass

    assert isinstance(exc_info.value.__cause__, ResponseError)


async def test_stream_raises_execution_error_on_connection_failure() -> None:
    provider, client = _make_provider()
    client.chat.side_effect = ConnectionError("cannot reach ollama server")

    with pytest.raises(GenerationExecutionError) as exc_info:
        async for _ in provider.stream(_make_request()):
            pass

    assert isinstance(exc_info.value.__cause__, ConnectionError)


async def test_health_check_returns_true_on_success() -> None:
    provider, client = _make_provider()

    assert await provider.health_check() is True
    client.ps.assert_awaited_once()


async def test_health_check_returns_false_without_raising_on_sdk_failure() -> None:
    provider, client = _make_provider()
    client.ps.side_effect = ConnectionError("server down")

    assert await provider.health_check() is False


async def test_get_model_metadata_includes_installed_models_on_success() -> None:
    provider, client = _make_provider()
    models_response = MagicMock()
    models_response.models = [MagicMock(model="llama3"), MagicMock(model="qwen3")]
    client.list.return_value = models_response

    metadata = await provider.get_model_metadata()

    assert metadata["installed_models"] == ["llama3", "qwen3"]
    assert metadata["provider"] == GenerationProvider.OLLAMA.value


async def test_get_model_metadata_returns_empty_list_without_raising_on_sdk_failure() -> None:
    provider, client = _make_provider()
    client.list.side_effect = ConnectionError("server down")

    metadata = await provider.get_model_metadata()

    assert metadata["installed_models"] == []


async def test_generate_structured_delegates_to_generate() -> None:
    provider, client = _make_provider()
    client.chat.return_value = _make_chat_response(content='{"ok": true}')

    result = await provider.generate_structured(
        _make_request(response_format=ResponseFormat.STRUCTURED)
    )

    assert result.parsed_output == {"ok": True}
