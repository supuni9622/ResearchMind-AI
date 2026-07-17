from __future__ import annotations

from app.ai.runtime.generation.caching.enums import (
    CacheLevel,
)
from pydantic import (
    BaseModel,
    ConfigDict,
)


class StreamCacheOutcome(BaseModel):
    """
    Carried in the START StreamEvent's metadata (`metadata["cache"]`) so a
    consumer can tell a replayed cache hit apart from a live stream without
    waiting for the whole thing to finish.
    """

    model_config = ConfigDict(extra="forbid")

    hit: bool
    level: CacheLevel | None = None
    replayed: bool = False
