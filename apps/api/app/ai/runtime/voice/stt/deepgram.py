"""Deepgram real-time streaming transcription over the raw WebSocket
protocol (developers.deepgram.com/reference/listen-live), not the
`deepgram-sdk` package.

Calling the vendor's documented wire protocol directly mirrors this
codebase's existing convention for the Web Search Tool Platform
(`TavilyWebSearchProvider` calls Tavily's REST API directly, no vendor SDK
dependency) and sidesteps coupling to `deepgram-sdk`'s own internal
class/method names, which have changed across major SDK versions (v1 vs v2
`connect` APIs) independently of the underlying wire protocol, which is
stable.
"""

from __future__ import annotations

import contextlib
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from urllib.parse import urlencode

import structlog
import websockets

from app.ai.runtime.voice.ws_connection import VoiceWebSocketConnection

logger = structlog.get_logger()

_LISTEN_URL = "wss://api.deepgram.com/v1/listen"


@dataclass(frozen=True, slots=True)
class TranscriptEvent:
    transcript: str
    is_final: bool


class DeepgramSTTProvider:
    """Stateless configuration holder -- one `connect()` call per
    conversational turn (see `voice.transcription.collect_voice_turn_transcript`),
    not one connection reused across turns."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        sample_rate: int,
        endpointing_ms: int,
        connect_timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._sample_rate = sample_rate
        self._endpointing_ms = endpointing_ms
        self._connect_timeout_seconds = connect_timeout_seconds

    def _connect_url(self) -> str:
        params = {
            "model": self._model,
            "encoding": "linear16",
            "sample_rate": str(self._sample_rate),
            "channels": "1",
            "punctuate": "true",
            "interim_results": "true",
            "endpointing": str(self._endpointing_ms),
        }
        return f"{_LISTEN_URL}?{urlencode(params)}"

    async def connect(self) -> VoiceWebSocketConnection:
        return await websockets.connect(
            self._connect_url(),
            additional_headers={"Authorization": f"Token {self._api_key}"},
            open_timeout=self._connect_timeout_seconds,
        )

    @staticmethod
    async def send_audio(connection: VoiceWebSocketConnection, chunk: bytes) -> None:
        await connection.send(chunk)

    @staticmethod
    async def close(connection: VoiceWebSocketConnection) -> None:
        """Best-effort: the connection may already be closed (e.g. Deepgram
        ended the session first), which is not an error worth surfacing --
        this is cleanup, not core turn logic."""

        with contextlib.suppress(websockets.exceptions.ConnectionClosed):
            await connection.send(json.dumps({"type": "CloseStream"}))
        with contextlib.suppress(websockets.exceptions.ConnectionClosed):
            await connection.close()

    @staticmethod
    async def transcripts(connection: VoiceWebSocketConnection) -> AsyncIterator[TranscriptEvent]:
        """Yields one `TranscriptEvent` per Deepgram `Results` message.
        Non-`Results` message types (e.g. `Metadata`) and empty-transcript
        results are silently skipped -- both are normal, documented
        occurrences in this protocol, not errors."""

        async for raw_message in connection:
            if isinstance(raw_message, bytes):
                continue

            try:
                payload = json.loads(raw_message)
            except json.JSONDecodeError:
                logger.warning("voice.stt.deepgram.malformed_message")
                continue

            if payload.get("type") != "Results":
                continue

            alternatives = payload.get("channel", {}).get("alternatives", [])
            if not alternatives:
                continue

            transcript = alternatives[0].get("transcript", "")
            if not transcript:
                continue

            yield TranscriptEvent(
                transcript=transcript,
                is_final=bool(payload.get("is_final", False)),
            )
