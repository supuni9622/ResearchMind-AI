from __future__ import annotations

import array
import asyncio
from collections.abc import AsyncGenerator, AsyncIterator, MutableMapping
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.ai.runtime.events.enums import CoreEventType, EventCategory
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.voice.response_stream import stream_voice_response
from app.ai.runtime.voice.ws_connection import VoiceWebSocketConnection
from app.core.settings import settings


def _loud_pcm16_chunk() -> bytes:
    return array.array("h", [10_000] * 160).tobytes()


class _DummyConnection:
    """Trivially satisfies `VoiceWebSocketConnection` -- `_FakeTTS` never
    actually reads/writes through it, it just needs something to hand
    back from `connect()`."""

    def __aiter__(self) -> _DummyConnection:
        return self

    async def __anext__(self) -> str:
        raise StopAsyncIteration

    async def send(self, data: str | bytes) -> None:  # noqa: ARG002
        pass

    async def close(self) -> None:
        pass


class _FakeWebSocket:
    """`receive()` reports an immediate disconnect by default -- the
    barge-in watcher task calls it, but with nothing to detect it just
    exits cleanly, same as a real client with no more audio to send."""

    def __init__(self) -> None:
        self.sent_json: list[dict] = []
        self.sent_bytes: list[bytes] = []

    async def receive(self) -> MutableMapping[str, Any]:
        return {"type": "websocket.disconnect", "code": 1000}

    async def send_json(self, data: Any) -> None:
        self.sent_json.append(data)

    async def send_bytes(self, data: bytes) -> None:
        self.sent_bytes.append(data)


class _LoudWebSocket(_FakeWebSocket):
    """`receive()` always returns a loud audio chunk -- forces a
    deterministic barge-in detection in tests."""

    async def receive(self) -> MutableMapping[str, Any]:
        await asyncio.sleep(0)
        return {"type": "websocket.receive", "bytes": _loud_pcm16_chunk()}


class _FakeTTS:
    def __init__(self, audio_chunks: list[bytes]) -> None:
        self._audio_chunks = audio_chunks
        self.sent_text: list[str] = []
        self.finished = False
        self.closed = False

    async def connect(self) -> VoiceWebSocketConnection:
        return _DummyConnection()

    async def send_text(self, connection: VoiceWebSocketConnection, text: str) -> None:  # noqa: ARG002
        self.sent_text.append(text)

    async def finish(self, connection: VoiceWebSocketConnection) -> None:  # noqa: ARG002
        self.finished = True

    async def close(self, connection: VoiceWebSocketConnection) -> None:  # noqa: ARG002
        self.closed = True

    async def audio_chunks(self, connection: VoiceWebSocketConnection) -> AsyncIterator[bytes]:  # noqa: ARG002
        for chunk in self._audio_chunks:
            yield chunk


async def _events(items: list[StreamEvent]) -> AsyncGenerator[StreamEvent, None]:
    for item in items:
        yield item


async def _slow_events(items: list[StreamEvent]) -> AsyncGenerator[StreamEvent, None]:
    """Same as `_events`, but yields control to the event loop between
    items -- gives the concurrent barge-in watcher task real chances to
    run, which a zero-await fake generator otherwise wouldn't."""

    for item in items:
        await asyncio.sleep(0)
        yield item


@pytest.mark.asyncio
async def test_none_tts_forwards_json_events_only() -> None:
    websocket = _FakeWebSocket()
    events = _events(
        [
            StreamEvent(
                category=EventCategory.GENERATION,
                type=CoreEventType.TOKEN.value,
                content="hi",
            ),
            StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value),
        ],
    )

    await stream_voice_response(websocket=websocket, events=events, tts=None)

    assert len(websocket.sent_json) == 2
    assert websocket.sent_bytes == []


@pytest.mark.asyncio
async def test_tokens_are_sentence_buffered_and_synthesized_then_finished() -> None:
    websocket = _FakeWebSocket()
    tts = _FakeTTS(audio_chunks=[b"chunk-1", b"chunk-2"])
    events = _events(
        [
            StreamEvent(
                category=EventCategory.GENERATION,
                type=CoreEventType.TOKEN.value,
                content="First sentence. ",
            ),
            StreamEvent(
                category=EventCategory.GENERATION,
                type=CoreEventType.TOKEN.value,
                content="Trailing partial",
            ),
            StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value),
        ],
    )

    await stream_voice_response(websocket=websocket, events=events, tts=tts)

    assert tts.sent_text == ["First sentence.", "Trailing partial"]
    assert tts.finished is True
    assert tts.closed is True
    assert websocket.sent_bytes == [b"chunk-1", b"chunk-2"]
    # The JSON events are still forwarded, same as the no-TTS path.
    assert len(websocket.sent_json) == 3


@pytest.mark.asyncio
async def test_records_first_audio_latency_metric_exactly_once() -> None:
    websocket = _FakeWebSocket()
    tts = _FakeTTS(audio_chunks=[b"a", b"b", b"c"])
    events = _events(
        [StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value)],
    )
    recorder = MagicMock()

    with patch(
        "app.ai.runtime.voice.response_stream.get_metrics_recorder",
        return_value=recorder,
    ):
        await stream_voice_response(websocket=websocket, events=events, tts=tts)

    assert recorder.record_duration.call_count == 1
    _, kwargs = recorder.record_duration.call_args
    assert kwargs["operation"] == "voice_tts_first_audio"


@pytest.mark.asyncio
async def test_barge_in_cuts_the_response_short_and_notifies_the_client(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voice_barge_in_enabled", True)
    monkeypatch.setattr(settings, "voice_barge_in_consecutive_chunks", 1)
    websocket = _LoudWebSocket()
    tts = _FakeTTS(audio_chunks=[b"chunk"] * 20)
    events = _slow_events(
        [
            StreamEvent(
                category=EventCategory.GENERATION,
                type=CoreEventType.TOKEN.value,
                content=f"word{i} ",
            )
            for i in range(20)
        ]
        + [StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value)],
    )

    await stream_voice_response(websocket=websocket, events=events, tts=tts)

    # Cut short: `finish()` (only sent on a normal COMPLETE) never ran.
    assert tts.finished is False
    assert tts.closed is True
    assert {"type": "voice.interrupted"} in websocket.sent_json
    # Did not forward every one of the 21 events -- the loop broke early.
    assert len(websocket.sent_json) < 21


@pytest.mark.asyncio
async def test_barge_in_disabled_lets_the_response_finish_normally(monkeypatch) -> None:
    monkeypatch.setattr(settings, "voice_barge_in_enabled", False)
    websocket = _LoudWebSocket()
    tts = _FakeTTS(audio_chunks=[b"chunk"])
    events = _slow_events(
        [StreamEvent(category=EventCategory.GENERATION, type=CoreEventType.COMPLETE.value)],
    )

    await stream_voice_response(websocket=websocket, events=events, tts=tts)

    assert tts.finished is True
    assert {"type": "voice.interrupted"} not in websocket.sent_json
