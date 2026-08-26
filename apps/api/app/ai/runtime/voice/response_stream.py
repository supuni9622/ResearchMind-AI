"""Sends a chat generation's `StreamEvent`s to a voice WebSocket exactly as
`run_websocket_stream` does for `/chat/ws`, while additionally tapping
TOKEN events into ElevenLabs streaming TTS and forwarding synthesized
audio as binary frames on the same connection (docs/todo/
voice-chat-poc-implementation-plan.md T8/T9).
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncGenerator

import structlog

from app.ai.observability.prometheus.create import get_metrics_recorder
from app.ai.runtime.events.enums import CoreEventType
from app.ai.runtime.events.models import StreamEvent
from app.ai.runtime.generation.models import StreamEventType
from app.ai.runtime.generation.streaming.serializers.json import serialize_json
from app.ai.runtime.voice.provider_sessions import TextToSpeechSession
from app.ai.runtime.voice.sentence_buffer import SentenceBuffer
from app.ai.runtime.voice.vad import BargeInDetector
from app.ai.runtime.voice.ws_connection import VoiceClientSocket
from app.core.settings import settings
from app.infrastructure.metrics.voice import VOICE_TTS_FIRST_AUDIO_DURATION

logger = structlog.get_logger()

_COMPLETION_EVENT_TYPES = {
    CoreEventType.COMPLETE.value,
    StreamEventType.COMPLETED.value,
}

# Bounds how long we wait for ElevenLabs to finish emitting trailing audio
# after `finish()` before giving up on the drain task -- a stuck vendor
# connection must not hang the whole voice turn indefinitely.
_AUDIO_DRAIN_TIMEOUT_SECONDS = 15.0


async def stream_voice_response(
    *,
    websocket: VoiceClientSocket,
    events: AsyncGenerator[StreamEvent, None],
    tts: TextToSpeechSession | None,
) -> None:
    """Forwards every event to the client as JSON, same as
    `run_websocket_stream`. When `tts` is configured, also buffers TOKEN
    content into sentences, streams them to ElevenLabs, and forwards the
    resulting audio as binary frames interleaved with the JSON frames.

    `tts=None` degrades to a text-only voice turn (transcript + text
    response, no spoken audio) rather than raising -- same "unconfigured
    deployment never crashes" convention as the rest of this app's optional
    integrations. In that case there is no audio playing to interrupt, so
    barge-in detection doesn't run either.

    Barge-in (T10): while the response streams, a concurrent task watches
    incoming audio frames for the user starting to speak again (energy-
    based, see `vad.py` -- not a second live Deepgram connection). On
    detection, the response loop stops, ElevenLabs synthesis and playback
    are cut short, and a `voice.interrupted` frame tells the client to
    stop playback immediately rather than let the rest of the answer play
    out. The audio that triggered the detection is not carried into the
    next turn's Deepgram session -- the caller simply starts a fresh
    `collect_voice_turn_transcript` call, which will pick up the user's
    continued speech a moment later. Untested against a live turn -- see
    the plan doc's T10/T14.
    """

    if tts is None:
        async for event in events:
            await websocket.send_json(serialize_json(event))
        return

    connection = await tts.connect()
    buffer = SentenceBuffer()
    tts_started_at = time.monotonic()
    first_audio_seen = False
    interrupted = asyncio.Event()

    async def _drain_audio() -> None:
        nonlocal first_audio_seen
        async for chunk in tts.audio_chunks(connection):
            if interrupted.is_set():
                return
            if not first_audio_seen:
                first_audio_seen = True
                get_metrics_recorder().record_duration(
                    operation=VOICE_TTS_FIRST_AUDIO_DURATION,
                    duration_ms=(time.monotonic() - tts_started_at) * 1000,
                )
            await websocket.send_bytes(chunk)

    async def _watch_for_barge_in() -> None:
        if not settings.voice_barge_in_enabled:
            return

        detector = BargeInDetector(
            rms_threshold=settings.voice_barge_in_rms_threshold,
            consecutive_chunks_required=settings.voice_barge_in_consecutive_chunks,
        )
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
            audio_chunk = message.get("bytes")
            if audio_chunk and detector.push(audio_chunk):
                interrupted.set()
                return

    drain_task = asyncio.create_task(_drain_audio())
    barge_in_task = asyncio.create_task(_watch_for_barge_in())

    try:
        async for event in events:
            if interrupted.is_set():
                break

            await websocket.send_json(serialize_json(event))

            if event.type == CoreEventType.TOKEN.value and event.content:
                for sentence in buffer.push(event.content):
                    await tts.send_text(connection, sentence)

            if event.type in _COMPLETION_EVENT_TYPES:
                remaining = buffer.flush()
                if remaining:
                    await tts.send_text(connection, remaining)
                await tts.finish(connection)

        if interrupted.is_set():
            logger.info("voice.chat.barged_in")
            await websocket.send_json({"type": "voice.interrupted"})
            await events.aclose()
    finally:
        barge_in_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await barge_in_task

        if interrupted.is_set():
            drain_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await drain_task
        else:
            try:
                await asyncio.wait_for(drain_task, timeout=_AUDIO_DRAIN_TIMEOUT_SECONDS)
            except TimeoutError:
                logger.warning("voice.tts.elevenlabs.drain_timed_out")
                drain_task.cancel()
            except asyncio.CancelledError:
                pass

        await tts.close(connection)
