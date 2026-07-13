"""
Retrieval fusion interfaces.

Fusion combines multiple retrieval result sets into a single
ranked result list.

Examples:

- Reciprocal Rank Fusion (RRF)
- Weighted Reciprocal Rank Fusion
- Score Fusion
- Relative Score Fusion
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.knowledge.retrieval.models import (
    RetrievalResult,
)


class FusionStrategy(ABC):
    """
    Base interface for retrieval fusion strategies.
    """

    @abstractmethod
    async def fuse(
        self,
        *,
        dense: RetrievalResult,
        sparse: RetrievalResult,
        top_k: int,
    ) -> RetrievalResult:
        """
        Fuse multiple retrieval result sets into a
        single ranked result.

        Parameters
        ----------
        dense:
            Dense retrieval results.

        sparse:
            Sparse retrieval results.

        top_k:
            Number of final chunks to return.

        Returns
        -------
        RetrievalResult
            Fused retrieval result.
        """
        raise NotImplementedError
