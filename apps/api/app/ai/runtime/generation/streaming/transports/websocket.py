from __future__ import annotations

from collections.abc import AsyncGenerator

import structlog
from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.streaming.serializers.json import (
    serialize_json,
)
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger()


async def run_websocket_stream(
    ws: WebSocket,
    events: AsyncGenerator[StreamEvent, None],
) -> None:
    """
    Sends each StreamEvent as a JSON frame over an already-accepted
    WebSocket connection. On a client disconnect, closes the underlying
    event generator so the in-flight generation is cancelled rather than
    left running with nothing consuming it.
    """

    try:
        async for event in events:
            await ws.send_json(
                serialize_json(event),
            )
    except WebSocketDisconnect:
        logger.info(
            "streaming.websocket.client_disconnected",
        )
    finally:
        await events.aclose()
