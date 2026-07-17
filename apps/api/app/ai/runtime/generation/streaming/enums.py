from __future__ import annotations

from enum import StrEnum


class StreamTransport(StrEnum):
    SSE = "sse"
    WEBSOCKET = "websocket"


class ValidationEventType(StrEnum):
    """
    Validation is a Generation Platform concern (see
    `generation/validation/service.py`), not a Layer 3 runtime, so this
    enum lives here rather than under `runtime/events/<domain>/` alongside
    Research/Agent/Tool. Not yet emitted by `StreamingService` -- reserved
    for when streamed requests grow output-validation support.
    """

    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
