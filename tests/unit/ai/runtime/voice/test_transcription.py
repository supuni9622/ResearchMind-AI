from __future__ import annotations

from collections.abc import AsyncIterator, MutableMapping
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from app.ai.runtime.voice.stt.deepgram import TranscriptEvent
from app.ai.runtime.voice.transcription import collect_voice_turn_transcript
from app.ai.runtime.voice.ws_connection import VoiceWebSocketConnection


class _DummyConnection:
    """Trivially satisfies `VoiceWebSocketConnection` -- the fake
    providers below never actually read/write through it, they just need
    something to hand back from `connect()`."""

    def __aiter__(self) -> _DummyConnection:
        return self

    async def __anext__(self) -> str:
        raise StopAsyncIteration

    async def send(self, data: str | bytes) -> None:  # noqa: ARG002
        pass

    async def close(self) -> None:
        pass


class _FakeSTT:
    """Stands in for `DeepgramSTTProvider`: `transcripts()` replays a
    canned event list, `connect`/`send_audio`/`close` are recorded."""

    def __init__(self, events: list[TranscriptEvent]) -> None:
        self._events = events
        self.closed = False

    async def connect(self) -> VoiceWebSocketConnection:
        return _DummyConnection()

    async def transcripts(
        self,
        connection: VoiceWebSocketConnection,  # noqa: ARG002
    ) -> AsyncIterator[TranscriptEvent]:
        for event in self._events:
            yield event

    async def send_audio(self, connection: VoiceWebSocketConnection, chunk: bytes) -> None:  # noqa: ARG002
        pass

    async def close(self, connection: VoiceWebSocketConnection) -> None:  # noqa: ARG002
        self.closed = True


class _FakeWebSocket:
    """`receive()` replays a canned message list, then reports
    disconnect forever; `send_json` records what was sent."""

    def __init__(self, messages: list[dict]) -> None:
        self._messages = list(messages)
        self.sent_json: list[dict] = []

    async def receive(self) -> MutableMapping[str, Any]:
        if self._messages:
            return self._messages.pop(0)
        return {"type": "websocket.disconnect", "code": 1000}

    async def send_json(self, data: Any) -> None:
        self.sent_json.append(data)

    async def send_bytes(self, data: bytes) -> None:
        raise NotImplementedError("collect_voice_turn_transcript never calls send_bytes()")


@pytest.mark.asyncio
async def test_returns_first_nonempty_final_transcript_and_forwards_interim_events() -> None:
    stt = _FakeSTT(
        [
            TranscriptEvent(transcript="hello", is_final=False),
            TranscriptEvent(transcript="hello world", is_final=True),
        ],
    )
    websocket = _FakeWebSocket([{"type": "websocket.receive", "bytes": b"\x00\x01"}])

    transcript = await collect_voice_turn_transcript(websocket=websocket, stt=stt)

    assert transcript == "hello world"
    assert websocket.sent_json == [
        {"type": "voice.transcript", "transcript": "hello", "is_final": False},
        {"type": "voice.transcript", "transcript": "hello world", "is_final": True},
    ]
    assert stt.closed is True


@pytest.mark.asyncio
async def test_returns_none_when_client_disconnects_before_a_final_transcript() -> None:
    stt = _FakeSTT([TranscriptEvent(transcript="still talking", is_final=False)])
    websocket = _FakeWebSocket([])  # disconnects immediately

    transcript = await collect_voice_turn_transcript(websocket=websocket, stt=stt)

    assert transcript is None
    assert stt.closed is True


@pytest.mark.asyncio
async def test_records_first_transcript_latency_metric_exactly_once() -> None:
    stt = _FakeSTT(
        [
            TranscriptEvent(transcript="one", is_final=False),
            TranscriptEvent(transcript="two", is_final=False),
            TranscriptEvent(transcript="final", is_final=True),
        ],
    )
    websocket = _FakeWebSocket([])
    recorder = MagicMock()

    with patch(
        "app.ai.runtime.voice.transcription.get_metrics_recorder",
        return_value=recorder,
    ):
        await collect_voice_turn_transcript(websocket=websocket, stt=stt)

    assert recorder.record_duration.call_count == 1
    _, kwargs = recorder.record_duration.call_args
    assert kwargs["operation"] == "voice_stt_first_transcript"
