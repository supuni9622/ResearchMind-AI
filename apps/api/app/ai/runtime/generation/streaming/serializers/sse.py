from __future__ import annotations

import json

from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.streaming.interfaces import (
    StreamSerializerInterface,
)
from app.ai.runtime.generation.streaming.serializers.json import (
    serialize_json,
)


def serialize_sse(event: StreamEvent) -> str:
    """
    `text/event-stream` wire format for one StreamEvent:

        event: <type>
        data: <json>
        <blank line>

    `event.type` is used as the SSE `event:` field verbatim -- it is
    already a plain string (see runtime/events/models.py), so no mapping
    is needed here.
    """

    payload = json.dumps(serialize_json(event))

    return f"event: {event.type}\ndata: {payload}\n\n"


class SSESerializer(StreamSerializerInterface):
    def serialize(self, event: StreamEvent) -> str:
        return serialize_sse(event)
