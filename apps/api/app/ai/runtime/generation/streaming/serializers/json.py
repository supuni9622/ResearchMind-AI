from __future__ import annotations

from typing import Any

from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.streaming.interfaces import (
    StreamSerializerInterface,
)


def serialize_json(event: StreamEvent) -> dict[str, Any]:
    """
    JSON-frame representation of a StreamEvent, used by the WebSocket
    transport (and by the SSE serializer for its `data:` line).
    """

    return event.model_dump(mode="json")


class JsonSerializer(StreamSerializerInterface):
    def serialize(self, event: StreamEvent) -> dict[str, Any]:
        return serialize_json(event)
