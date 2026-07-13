"""
Reciprocal Rank Fusion (RRF).

RRF is a robust ranking algorithm that combines multiple
retrieval result sets using ranking positions instead of
raw similarity scores.

Formula:

score += 1 / (k + rank)

References:
    Cormack et al.
    "Reciprocal Rank Fusion Outperforms Condorcet and
    Individual Rank Learning Methods"
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from app.ai.knowledge.retrieval.fusion.interfaces import (
    FusionStrategy,
)
from app.ai.knowledge.retrieval.models import (
    RetrievalExecution,
    RetrievalResult,
    RetrievedChunk,
)


class ReciprocalRankFusion(
    FusionStrategy,
):
    """
    Reciprocal Rank Fusion.

    Default k=60 follows the original paper and is also
    commonly used by Elasticsearch and Azure AI Search.
    """

    def __init__(
        self,
        *,
        k: int = 60,
    ) -> None:
        self._k = k

    async def fuse(
        self,
        *,
        dense: RetrievalResult,
        sparse: RetrievalResult,
        top_k: int,
    ) -> RetrievalResult:
        """
        Fuse dense and sparse retrieval results.
        """

        scores: dict[
            str,
            float,
        ] = defaultdict(float)

        chunks: dict[
            str,
            RetrievedChunk,
        ] = {}

        #
        # Dense rankings
        #

        for rank, chunk in enumerate(
            dense.chunks,
            start=1,
        ):
            key = str(
                chunk.chunk_id,
            )

            scores[key] += 1.0 / (self._k + rank)

            chunks[key] = chunk

        #
        # Sparse rankings
        #

        for rank, chunk in enumerate(
            sparse.chunks,
            start=1,
        ):
            key = str(
                chunk.chunk_id,
            )

            scores[key] += 1.0 / (self._k + rank)

            #
            # Keep first copy if already exists.
            #

            if key not in chunks:
                chunks[key] = chunk

        #
        # Sort by RRF score.
        #

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        fused_chunks: list[RetrievedChunk] = []

        for (
            chunk_id,
            score,
        ) in ranked[:top_k]:
            original = chunks[chunk_id]

            #
            # Avoid mutating
            # dense/sparse results.
            #

            fused_chunk = original.model_copy(
                update={
                    "score": score,
                }
            )

            fused_chunks.append(
                fused_chunk,
            )

        return RetrievalResult(
            query=dense.query,
            execution=RetrievalExecution(
                completed_at=datetime.now(UTC),
            ),
            chunks=fused_chunks,
        )
