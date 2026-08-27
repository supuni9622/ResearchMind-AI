from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, patch

import pytest
from app.ai.runtime.voice.tts.elevenlabs import ElevenLabsTTSProvider


class _FakeConnection:
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


def _provider() -> ElevenLabsTTSProvider:
    return ElevenLabsTTSProvider(
        api_key="el-secret",
        voice_id="voice-123",
        model_id="eleven_flash_v2_5",
        output_format="mp3_44100_128",
        connect_timeout_seconds=5.0,
    )


@pytest.mark.asyncio
async def test_connect_sends_xi_api_key_header_and_init_message() -> None:
    fake_connection = _FakeConnection([])

    with patch(
        "app.ai.runtime.voice.tts.elevenlabs.websockets.connect",
        new=AsyncMock(return_value=fake_connection),
    ) as connect:
        result = await _provider().connect()

    args, kwargs = connect.call_args
    url = args[0]
    assert url == (
        "wss://api.elevenlabs.io/v1/text-to-speech/voice-123/stream-input"
        "?model_id=eleven_flash_v2_5&output_format=mp3_44100_128"
    )
    assert kwargs["additional_headers"] == {"xi-api-key": "el-secret"}
    assert kwargs["open_timeout"] == 5.0

    assert result is fake_connection
    init_message = json.loads(fake_connection.sent[0])
    assert init_message["text"] == " "
    assert "voice_settings" in init_message


@pytest.mark.asyncio
async def test_send_text_appends_trailing_space_required_by_protocol() -> None:
    connection = _FakeConnection([])

    await ElevenLabsTTSProvider.send_text(connection, "Hello there")
    await ElevenLabsTTSProvider.send_text(connection, "Already has one ")
    await ElevenLabsTTSProvider.send_text(connection, "")

    assert json.loads(connection.sent[0])["text"] == "Hello there "
    assert json.loads(connection.sent[1])["text"] == "Already has one "
    # Empty text is a no-op, not an empty protocol message.
    assert len(connection.sent) == 2


@pytest.mark.asyncio
async def test_finish_sends_empty_text_message() -> None:
    connection = _FakeConnection([])

    await ElevenLabsTTSProvider.finish(connection)

    assert json.loads(connection.sent[0])["text"] == ""


@pytest.mark.asyncio
async def test_audio_chunks_decodes_base64_and_stops_on_is_final() -> None:
    first_audio = base64.b64encode(b"chunk-one").decode()
    second_audio = base64.b64encode(b"chunk-two").decode()
    connection = _FakeConnection(
        [
            json.dumps({"audio": first_audio}),
            json.dumps({"audio": second_audio, "isFinal": True}),
            json.dumps({"audio": base64.b64encode(b"never-yielded").decode()}),
        ],
    )

    chunks = [chunk async for chunk in ElevenLabsTTSProvider.audio_chunks(connection)]

    assert chunks == [b"chunk-one", b"chunk-two"]
