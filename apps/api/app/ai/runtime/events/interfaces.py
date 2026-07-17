from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.models import (
    StreamChunk,
)


class ProviderEventAdapterInterface(ABC):
    """
    Converts a provider's normalized StreamChunk into a canonical
    StreamEvent.

    Every provider's `stream()` already normalizes its SDK-specific chunks
    into the identical `StreamChunk` shape before anything leaves the
    provider (see generation/providers/*.py), so this is a StreamChunk ->
    StreamEvent normalizer rather than a per-SDK adapter.
    """

    @abstractmethod
    def to_stream_event(
        self,
        chunk: StreamChunk,
        *,
        session_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> StreamEvent:
        pass
