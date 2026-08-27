"""Structural types for the voice slice's narrow use of two larger
third-party classes: `websockets.asyncio.client.ClientConnection` (the
vendor-facing connection `DeepgramSTTProvider`/`ElevenLabsTTSProvider`
open) and FastAPI's `WebSocket` (the client-facing connection
`transcription.py`/`response_stream.py` read/write).

Each is a `Protocol` covering only the handful of methods actually
called, so a test fake only needs to satisfy that narrow shape rather
than inherit from (or fully re-implement) the real class. Deliberately
has zero imports from elsewhere in this package (see
`provider_sessions.py` for the STT/TTS provider protocols, split into
their own module to avoid a circular import with `stt/deepgram.py`)."""

from __future__ import annotations

from collections.abc import AsyncIterator, MutableMapping
from typing import Any, Protocol


class VoiceWebSocketConnection(Protocol):
    """The vendor-facing WebSocket connection surface
    (`DeepgramSTTProvider`/`ElevenLabsTTSProvider` methods) actually use."""

    def __aiter__(self) -> AsyncIterator[str | bytes]: ...

    async def send(self, data: str | bytes) -> None: ...

    async def close(self) -> None: ...


class VoiceClientSocket(Protocol):
    """The client-facing FastAPI `WebSocket` surface
    `transcription.collect_voice_turn_transcript` and
    `response_stream.stream_voice_response` actually use."""

    async def receive(self) -> MutableMapping[str, Any]: ...

    async def send_json(self, data: Any) -> None: ...

    async def send_bytes(self, data: bytes) -> None: ...
