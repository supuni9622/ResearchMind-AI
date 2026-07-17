from __future__ import annotations

from uuid import UUID

from app.ai.runtime.events.enums import (
    EventCategory,
)
from app.ai.runtime.events.interfaces import (
    ProviderEventAdapterInterface,
)
from app.ai.runtime.events.models import (
    StreamEvent,
)
from app.ai.runtime.generation.models import (
    StreamChunk,
)


class GenericStreamChunkAdapter(ProviderEventAdapterInterface):
    """
    Single adapter shared by every generation provider.

    Every provider's `stream()` already normalizes its SDK-specific chunks
    into the identical `StreamChunk` shape (see generation/providers/*.py),
    so there is nothing provider-specific left to adapt here. A separate
    near-identical adapter file per provider (openai.py, claude.py, ...)
    would itself be the provider-duplication ADR-028 rejects — a provider
    only needs its own adapter if its `stream()` ever emits something
    `StreamChunk` can't represent, which none do today.
    """

    def to_stream_event(
        self,
        chunk: StreamChunk,
        *,
        session_id: UUID | None = None,
        request_id: UUID | None = None,
    ) -> StreamEvent:

        return StreamEvent(
            session_id=session_id,
            request_id=request_id,
            category=EventCategory.GENERATION,
            type=chunk.event.value,
            content=chunk.content,
            metadata=chunk.metadata,
        )
