"""
Runtime Event Platform composition root.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.runtime.events.adapters.base import (
    GenericStreamChunkAdapter,
)
from app.ai.runtime.events.interfaces import (
    ProviderEventAdapterInterface,
)


@lru_cache
def get_event_adapter() -> ProviderEventAdapterInterface:
    """
    Return the singleton StreamChunk -> StreamEvent adapter.

    One adapter serves every provider today (see GenericStreamChunkAdapter's
    docstring for why this isn't a per-provider registry).
    """

    return GenericStreamChunkAdapter()
