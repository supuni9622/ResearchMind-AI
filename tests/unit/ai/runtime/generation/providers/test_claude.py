"""
Unit tests for ClaudeProvider.

Covers:
- Provider identifier
- generate() happy path: text-block extraction, usage (input+output, no
  SDK-provided total), finish_reason from stop_reason
- generate() extracts tool_use content blocks into tool_calls
- generate() with a response carrying no usage data
- generate() best-effort JSON parsing for JSON/STRUCTURED response formats
- generate() retries transient failures and eventually raises
  GenerationExecutionError, preserving the original exception as __cause__
- stream() yields START, TOKEN, COMPLETED and only reacts to
  content_block_delta events with text
- stream() coerces a missing system prompt to "" (Anthropic rejects None)
- stream() wraps SDK failures in GenerationExecutionError
- generate_structured() delegates to generate()
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic import AnthropicError
from app.ai.knowledge.context.models import PromptContext
from app.ai.runtime.generation.config import ClaudeGenerationConfig
from app.ai.runtime.generation.enums import GenerationProvider, ResponseFormat
from app.ai.runtime.generation.exceptions import GenerationExecutionError
from app.ai.runtime.generation.models import GenerationRequest, StreamEventType
from app.ai.runtime.generation.providers.claude import ClaudeProvider
from app.core.settings import settings


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
    system_prompt: str | None = None,
) -> GenerationRequest:
    return GenerationRequest(
        prompt_context=PromptContext(context="retrieved context", chunks=[]),
        user_prompt=user_prompt,
        response_format=response_format,
        system_prompt=system_prompt,
    )


def _make_provider(
    monkeypatch: pytest.MonkeyPatch, **config_overrides
) -> tuple[ClaudeProvider, MagicMock]:
    """
    Returns the provider plus a directly-typed handle to its mocked SDK
    client. Anthropic's SDK ships precise type stubs, so mypy resolves
    `provider._client...` back to the real AsyncAnthropic method
    signatures (which have no `.return_value`/`.side_effect`);
    configuring and asserting against the `client` handle returned here
    instead keeps the test file mypy-clean without weakening what's
    being verified.
    """

    monkeypatch.setattr(settings, "anthropic_api_key", "test-claude-key")

    config = ClaudeGenerationConfig(
        cost_per_input_1m=0.1,
        cost_per_output_1m=0.1,
        **config_overrides,
    )
    provider = ClaudeProvider(config=config)
    client = MagicMock()
    client.messages.create = AsyncMock()
    provider._client = client
    return provider, client


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _tool_use_block(tool_id: str, name: str, tool_input: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=tool_id, name=name, input=tool_input)


def _make_message(
    *,
    content: list | None = None,
    stop_reason: str = "end_turn",
    input_tokens: int = 10,
    output_tokens: int = 5,
    has_usage: bool = True,
) -> MagicMock:
    response = MagicMock()
    response.content = content if content is not None else [_text_block("hello world")]
    response.stop_reason = stop_reason
    response.model_dump.return_value = {"id": "msg-test"}

    if has_usage:
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
    else:
        response.usage = None

    return response


def _make_event(event_type: str, delta_text: str | None = None) -> SimpleNamespace:
    if delta_text is None:
        return SimpleNamespace(type=event_type)
    return SimpleNamespace(type=event_type, delta=SimpleNamespace(text=delta_text))


def test_provider_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    provider, _ = _make_provider(monkeypatch)

    assert provider.provider == GenerationProvider.CLAUDE


async def test_generate_returns_result_with_expected_content_and_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message()

    result = await provider.generate(_make_request())

    assert result.content == "hello world"
    assert result.finish_reason == "end_turn"
    assert result.provider == GenerationProvider.CLAUDE
    assert result.statistics.prompt_tokens == 10
    assert result.statistics.completion_tokens == 5
    assert result.statistics.total_tokens == 15
    assert result.raw_response == {"id": "msg-test"}


async def test_generate_joins_multiple_text_blocks_and_skips_non_text_blocks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message(
        content=[
            _text_block("first"),
            _tool_use_block("tool_1", "search", {"query": "x"}),
            _text_block("second"),
        ]
    )

    result = await provider.generate(_make_request())

    assert result.content == "first\nsecond"


async def test_generate_extracts_tool_use_blocks_into_tool_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message(
        content=[
            _text_block("using a tool"),
            _tool_use_block("tool_1", "search", {"query": "x"}),
        ]
    )

    result = await provider.generate(_make_request())

    assert result.tool_calls == [{"id": "tool_1", "name": "search", "input": {"query": "x"}}]


async def test_generate_handles_missing_usage_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message(has_usage=False)

    result = await provider.generate(_make_request())

    assert result.statistics.prompt_tokens == 0
    assert result.statistics.completion_tokens == 0
    assert result.statistics.total_tokens == 0


async def test_generate_parses_json_when_response_format_is_structured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message(
        content=[_text_block('{"answer": 42}')],
    )

    result = await provider.generate(_make_request(response_format=ResponseFormat.STRUCTURED))

    assert result.parsed_output == {"answer": 42}


async def test_generate_leaves_parsed_output_none_for_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message(
        content=[_text_block("not valid json")],
    )

    result = await provider.generate(_make_request(response_format=ResponseFormat.JSON))

    assert result.parsed_output is None


async def test_generate_coerces_missing_system_prompt_to_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message()

    await provider.generate(_make_request(system_prompt=None))

    _, kwargs = client.messages.create.call_args
    assert kwargs["system"] == ""


async def test_generate_retries_then_raises_execution_error_on_persistent_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    provider, client = _make_provider(monkeypatch, max_retries=1)
    client.messages.create.side_effect = AnthropicError("overloaded")

    with pytest.raises(GenerationExecutionError) as exc_info:
        await provider.generate(_make_request())

    assert isinstance(exc_info.value.__cause__, AnthropicError)
    assert client.messages.create.await_count == 2


async def test_stream_yields_start_token_and_completed_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _AsyncIter(
        [
            _make_event("message_start"),
            _make_event("content_block_delta", delta_text="Hello"),
            _make_event("content_block_delta", delta_text=" world"),
            _make_event("message_stop"),
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


async def test_stream_coerces_missing_system_prompt_to_empty_string(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _AsyncIter([])

    async for _ in provider.stream(_make_request(system_prompt=None)):
        pass

    _, kwargs = client.messages.create.call_args
    assert kwargs["system"] == ""


async def test_stream_raises_execution_error_on_sdk_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.side_effect = AnthropicError("auth failed")

    with pytest.raises(GenerationExecutionError) as exc_info:
        async for _ in provider.stream(_make_request()):
            pass

    assert isinstance(exc_info.value.__cause__, AnthropicError)


async def test_generate_structured_delegates_to_generate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider, client = _make_provider(monkeypatch)
    client.messages.create.return_value = _make_message(
        content=[_text_block('{"ok": true}')],
    )

    result = await provider.generate_structured(
        _make_request(response_format=ResponseFormat.STRUCTURED)
    )

    assert result.parsed_output == {"ok": True}
