from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.ai.runtime.events.models import (
    StreamEvent,
)


class StreamSerializerInterface(ABC):
    """
    Converts a canonical StreamEvent into whatever wire format a
    transport needs. Kept separate from the transports themselves so the
    same serialization logic (e.g. the SSE wire format) can be reused
    outside of a FastAPI response if needed later (tests, replay tooling).
    """

    @abstractmethod
    def serialize(
        self,
        event: StreamEvent,
    ) -> str | dict[str, Any]:
        pass
