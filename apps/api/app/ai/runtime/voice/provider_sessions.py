"""Structural types for `DeepgramSTTProvider`/`ElevenLabsTTSProvider`,
covering only what `transcription.py`/`response_stream.py` actually call.

Split out from `ws_connection.py` specifically to avoid a circular
import: this module needs `TranscriptEvent` from `stt/deepgram.py`, and
`stt/deepgram.py` needs `VoiceWebSocketConnection` from
`ws_connection.py` -- putting both protocol groups in one file would
make `ws_connection.py` and `stt/deepgram.py` import each other."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from app.ai.runtime.voice.stt.deepgram import TranscriptEvent
from app.ai.runtime.voice.ws_connection import VoiceWebSocketConnection


class SpeechToTextSession(Protocol):
    """The `DeepgramSTTProvider` surface `transcription.py` actually uses."""

    async def connect(self) -> VoiceWebSocketConnection: ...

    async def send_audio(self, connection: VoiceWebSocketConnection, chunk: bytes) -> None: ...

    async def close(self, connection: VoiceWebSocketConnection) -> None: ...

    def transcripts(
        self,
        connection: VoiceWebSocketConnection,
    ) -> AsyncIterator[TranscriptEvent]: ...


class TextToSpeechSession(Protocol):
    """The `ElevenLabsTTSProvider` surface `response_stream.py` actually
    uses."""

    async def connect(self) -> VoiceWebSocketConnection: ...

    async def send_text(self, connection: VoiceWebSocketConnection, text: str) -> None: ...

    async def finish(self, connection: VoiceWebSocketConnection) -> None: ...

    async def close(self, connection: VoiceWebSocketConnection) -> None: ...

    def audio_chunks(self, connection: VoiceWebSocketConnection) -> AsyncIterator[bytes]: ...
