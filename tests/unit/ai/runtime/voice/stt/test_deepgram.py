from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from app.ai.runtime.voice.stt.deepgram import DeepgramSTTProvider, TranscriptEvent


class _FakeConnection:
    """Stands in for `websockets.asyncio.client.ClientConnection`: async
    iteration yields preset raw messages, `send`/`close` are recorded."""

    def __init__(self, messages: list[str | bytes]) -> None:
        self._messages = list(messages)
        self.sent: list[str | bytes] = []
        self.closed = False

    def __aiter__(self) -> _FakeConnection:
        return self

    async def __anext__(self) -> str | bytes:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)

    async def send(self, data: str | bytes) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True


def _provider() -> DeepgramSTTProvider:
    return DeepgramSTTProvider(
        api_key="dg-secret",
        model="nova-3",
        sample_rate=16000,
        endpointing_ms=300,
        connect_timeout_seconds=5.0,
    )


@pytest.mark.asyncio
async def test_connect_sends_token_auth_header_and_expected_query_params() -> None:
    with patch(
        "app.ai.runtime.voice.stt.deepgram.websockets.connect",
        new=AsyncMock(return_value=_FakeConnection([])),
    ) as connect:
        await _provider().connect()

    args, kwargs = connect.call_args
    url = args[0]
    assert url.startswith("wss://api.deepgram.com/v1/listen?")
    assert "model=nova-3" in url
    assert "sample_rate=16000" in url
    assert "interim_results=true" in url
    assert kwargs["additional_headers"] == {"Authorization": "Token dg-secret"}
    assert kwargs["open_timeout"] == 5.0


@pytest.mark.asyncio
async def test_transcripts_yields_only_results_messages_with_nonempty_text() -> None:
    connection = _FakeConnection(
        [
            json.dumps({"type": "Metadata"}),
            json.dumps(
                {
                    "type": "Results",
                    "is_final": False,
                    "channel": {"alternatives": [{"transcript": "hello"}]},
                },
            ),
            json.dumps(
                {
                    "type": "Results",
                    "is_final": False,
                    "channel": {"alternatives": [{"transcript": ""}]},
                },
            ),
            json.dumps(
                {
                    "type": "Results",
                    "is_final": True,
                    "channel": {"alternatives": [{"transcript": "hello world"}]},
                },
            ),
            b"\x00\x01",  # binary frames (none expected from Deepgram) are skipped
            "not json",
        ],
    )

    events = [event async for event in DeepgramSTTProvider.transcripts(connection)]

    assert events == [
        TranscriptEvent(transcript="hello", is_final=False),
        TranscriptEvent(transcript="hello world", is_final=True),
    ]


@pytest.mark.asyncio
async def test_close_sends_close_stream_then_closes_connection() -> None:
    connection = _FakeConnection([])

    await DeepgramSTTProvider.close(connection)

    assert connection.sent == [json.dumps({"type": "CloseStream"})]
    assert connection.closed is True
