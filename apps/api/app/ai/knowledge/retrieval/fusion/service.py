from __future__ import annotations

from app.ai.knowledge.retrieval.fusion.rrf import (
    ReciprocalRankFusion,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalResult,
)


class RetrievalFusionService:
    def __init__(
        self,
    ) -> None:
        self._strategy = ReciprocalRankFusion()

    async def fuse(
        self,
        dense: RetrievalResult,
        sparse: RetrievalResult,
        top_k: int,
        metadata: RetrievalResult | None = None,
    ) -> RetrievalResult:

        return await self._strategy.fuse(
            dense=dense,
            sparse=sparse,
            top_k=top_k,
            metadata=metadata,
        )
