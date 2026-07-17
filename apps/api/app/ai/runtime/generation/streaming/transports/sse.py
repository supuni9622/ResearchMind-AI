from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncGenerator, AsyncIterator

import structlog
from app.ai.runtime.events.enums import (
    CoreEventType,
    EventCategory,
)
from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.streaming.serializers.sse import (
    serialize_sse,
)
from fastapi.responses import StreamingResponse

logger = structlog.get_logger()

#
# Production considerations (see ADR-028 / streaming-platform architecture
# doc): an idle SSE connection can be dropped by a browser or an
# intermediary load balancer with its own idle-connection timeout, so a
# heartbeat comment line is sent whenever nothing real has gone out for a
# while. A hard duration ceiling guards against a hung provider stream
# holding a connection (and a server worker) open indefinitely.
#
HEARTBEAT_INTERVAL_SECONDS = 15
MAX_STREAM_DURATION_SECONDS = 300

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    # Disables nginx/other proxy response buffering so chunks reach the
    # client as they're produced instead of once the whole body is ready.
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


async def _sse_byte_stream(
    events: AsyncGenerator[StreamEvent, None],
) -> AsyncIterator[bytes]:

    started = time.monotonic()

    try:
        while True:
            if time.monotonic() - started > MAX_STREAM_DURATION_SECONDS:
                logger.warning(
                    "streaming.sse.max_duration_exceeded",
                    max_duration_seconds=MAX_STREAM_DURATION_SECONDS,
                )

                yield serialize_sse(
                    StreamEvent(
                        category=EventCategory.GENERATION,
                        type=CoreEventType.ERROR.value,
                        content="Stream exceeded maximum duration.",
                    )
                ).encode("utf-8")

                return

            try:
                event = await asyncio.wait_for(
                    events.__anext__(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except TimeoutError:
                yield b": ping\n\n"
                continue
            except StopAsyncIteration:
                return

            yield serialize_sse(event).encode("utf-8")
    finally:
        await events.aclose()


def sse_stream_response(
    events: AsyncGenerator[StreamEvent, None],
) -> StreamingResponse:
    """
    Wraps a StreamEvent iterator as a `text/event-stream` FastAPI response.
    """

    return StreamingResponse(
        _sse_byte_stream(events),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
