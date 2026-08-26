"""Per-turn glue between a client's raw audio WebSocket frames and a
Deepgram streaming STT connection."""

from __future__ import annotations

import asyncio
import contextlib
import time

import structlog
import websockets

from app.ai.observability.prometheus.create import get_metrics_recorder
from app.ai.runtime.voice.provider_sessions import SpeechToTextSession
from app.ai.runtime.voice.ws_connection import VoiceClientSocket
from app.infrastructure.metrics.voice import VOICE_STT_FIRST_TRANSCRIPT_DURATION

logger = structlog.get_logger()


async def collect_voice_turn_transcript(
    *,
    websocket: VoiceClientSocket,
    stt: SpeechToTextSession,
) -> str | None:
    """Opens one Deepgram connection for a single conversational turn:
    forwards client audio frames to it, forwards Deepgram's interim/final
    transcripts back to the client as `voice.transcript` JSON frames, and
    returns the first non-empty final transcript.

    Returns `None` if the client disconnects before producing one -- there
    is no partial turn to act on in that case.

    One Deepgram connection per turn, not one for the whole call: trades a
    small per-turn reconnect cost for a much simpler lifecycle with no
    state to reconcile across turns, and rules out two overlapping turns
    ever triggering concurrent chat generations. This function only
    covers listening for the *next* turn -- barge-in during a still-
    playing response is handled separately, in
    `response_stream.stream_voice_response` (T10), not here.
    """

    connection = await stt.connect()
    turn_started_at = time.monotonic()
    first_transcript_seen = False

    try:

        async def _pump_audio() -> None:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                audio_chunk = message.get("bytes")
                if audio_chunk:
                    await stt.send_audio(connection, audio_chunk)

        async def _collect_final() -> str | None:
            nonlocal first_transcript_seen
            async for event in stt.transcripts(connection):
                if not first_transcript_seen:
                    first_transcript_seen = True
                    get_metrics_recorder().record_duration(
                        operation=VOICE_STT_FIRST_TRANSCRIPT_DURATION,
                        duration_ms=(time.monotonic() - turn_started_at) * 1000,
                    )
                await websocket.send_json(
                    {
                        "type": "voice.transcript",
                        "transcript": event.transcript,
                        "is_final": event.is_final,
                    },
                )
                if event.is_final and event.transcript.strip():
                    return event.transcript
            return None

        pump_task = asyncio.create_task(_pump_audio())
        collect_task = asyncio.create_task(_collect_final())

        done, pending = await asyncio.wait(
            {pump_task, collect_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        for task in done:
            exc = task.exception()
            if exc is not None and not isinstance(exc, websockets.exceptions.ConnectionClosed):
                raise exc

        if collect_task in done and not collect_task.cancelled():
            return collect_task.result()

        return None
    finally:
        await stt.close(connection)
