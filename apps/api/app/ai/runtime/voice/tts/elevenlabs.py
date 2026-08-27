"""ElevenLabs streaming text-to-speech over the raw WebSocket protocol
(elevenlabs.io/docs/api-reference/text-to-speech/v-1-text-to-speech-voice-id-stream-input),
not the `elevenlabs` SDK package -- same rationale as
`voice.stt.deepgram`'s direct-protocol choice: mirrors this codebase's
existing vendor-integration convention (`TavilyWebSearchProvider`) and
avoids coupling to SDK-internal names.
"""

from __future__ import annotations

import base64
import contextlib
import json
from collections.abc import AsyncIterator
from urllib.parse import urlencode

import structlog
import websockets

from app.ai.runtime.voice.ws_connection import VoiceWebSocketConnection

logger = structlog.get_logger()

_TTS_URL_TEMPLATE = "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"


class ElevenLabsTTSProvider:
    """Stateless configuration holder -- one `connect()` call per
    conversational turn (see `voice.response_stream.stream_voice_response`),
    matching `DeepgramSTTProvider`'s per-turn-connection lifecycle."""

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model_id: str,
        output_format: str,
        connect_timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._output_format = output_format
        self._connect_timeout_seconds = connect_timeout_seconds

    def _connect_url(self) -> str:
        params = {"model_id": self._model_id, "output_format": self._output_format}
        return f"{_TTS_URL_TEMPLATE.format(voice_id=self._voice_id)}?{urlencode(params)}"

    async def connect(self) -> VoiceWebSocketConnection:
        connection = await websockets.connect(
            self._connect_url(),
            additional_headers={"xi-api-key": self._api_key},
            open_timeout=self._connect_timeout_seconds,
        )
        # Required init message per the documented protocol -- a lone space
        # opens the generation session without emitting audio for it yet.
        await connection.send(
            json.dumps(
                {
                    "text": " ",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                    },
                },
            ),
        )
        return connection

    @staticmethod
    async def send_text(connection: VoiceWebSocketConnection, text: str) -> None:
        if not text:
            return
        # Protocol requires text chunks to end with a space.
        payload = text if text.endswith(" ") else f"{text} "
        await connection.send(json.dumps({"text": payload}))

    @staticmethod
    async def finish(connection: VoiceWebSocketConnection) -> None:
        """Signals no more text is coming -- lets ElevenLabs flush and emit
        the final audio chunk(s) instead of holding a partial sentence."""

        await connection.send(json.dumps({"text": ""}))

    @staticmethod
    async def close(connection: VoiceWebSocketConnection) -> None:
        with contextlib.suppress(websockets.exceptions.ConnectionClosed):
            await connection.close()

    @staticmethod
    async def audio_chunks(connection: VoiceWebSocketConnection) -> AsyncIterator[bytes]:
        """Yields decoded audio bytes as ElevenLabs produces them, ending
        when the `isFinal` completion message arrives."""

        async for raw_message in connection:
            if isinstance(raw_message, bytes):
                continue

            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                logger.warning("voice.tts.elevenlabs.malformed_message")
                continue

            audio_b64 = payload.get("audio")
            if audio_b64:
                yield base64.b64decode(audio_b64)

            if payload.get("isFinal"):
                return
