from __future__ import annotations

import asyncio
import contextlib
import time
from collections.abc import AsyncGenerator, AsyncIterator
from typing import Any, Literal

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

_QueueItem = tuple[Literal["event", "error", "done"], Any]

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


async def _pump(
    events: AsyncGenerator[StreamEvent, None],
    queue: asyncio.Queue[_QueueItem],
) -> None:
    """
    Drives `events` to completion from a single, stable Task/context.

    This matters beyond convenience: the LangSmith tracer wrapping the
    underlying generator does `current_run_id.set(...)` once and
    `current_run_id.reset(token)` once, potentially many `yield`s apart.
    `contextvars.Token.reset()` requires the exact `Context` it was
    created in -- if each `__anext__()` call were awaited from a
    *different* Task (each with its own copied context), the reset
    would raise `ValueError: ... was created in a different Context`.
    Pumping the whole generator from one Task keeps every `set()`/
    `reset()` pair inside the same context throughout.
    """

    try:
        async for event in events:
            await queue.put(("event", event))
    except Exception as exc:
        await queue.put(("error", exc))
        return
    finally:
        #
        # Closed here (same Task/context as any `set()` above) rather
        # than by the consumer loop, for the same contextvars reason --
        # and so a still-open trace is properly finalized even when
        # the consumer stops early (client disconnect, duration ceiling).
        #
        await events.aclose()

    await queue.put(("done", None))


async def _sse_byte_stream(
    events: AsyncGenerator[StreamEvent, None],
) -> AsyncIterator[bytes]:

    started = time.monotonic()
    queue: asyncio.Queue[_QueueItem] = asyncio.Queue(maxsize=64)
    pump_task = asyncio.ensure_future(_pump(events, queue))

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
                kind, payload = await asyncio.wait_for(
                    queue.get(),
                    timeout=HEARTBEAT_INTERVAL_SECONDS,
                )
            except TimeoutError:
                #
                # Nothing new yet -- ping so the connection isn't dropped
                # as idle. This only ever cancels the lightweight
                # `queue.get()`, never the in-flight generation/
                # persistence work still running inside `_pump`.
                #
                yield b": ping\n\n"
                continue

            if kind == "done":
                return

            if kind == "error":
                raise payload

            yield serialize_sse(payload).encode("utf-8")
    finally:
        pump_task.cancel()
        with contextlib.suppress(BaseException):
            await pump_task


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
