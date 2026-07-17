"""
Generation Streaming Platform composition root.

Mirrors `generation/create.py` / `caching/create.py`'s composition-root
style.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.runtime.events.create import (
    get_event_adapter,
)
from app.ai.runtime.generation.caching.create import (
    create_caching_service,
)
from app.ai.runtime.generation.create import (
    create_generation_service,
)
from app.ai.runtime.generation.streaming.service import (
    StreamingService,
)


@lru_cache
def create_streaming_service() -> StreamingService:
    """
    Create a fully configured StreamingService.

    Reuses `create_generation_service()`'s own registry (via
    `GenerationService.registry`) rather than composing a second one, so
    the same provider instances are shared instead of duplicated.
    """

    generation_service = create_generation_service()

    return StreamingService(
        generation_service=generation_service,
        registry=generation_service.registry,
        event_adapter=get_event_adapter(),
        caching_service=create_caching_service(),
    )
