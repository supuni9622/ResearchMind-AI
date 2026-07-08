"""
Indexing Platform interfaces.

The Indexing Platform is responsible for transforming embedding artifacts
into one or more searchable indexes.

This interface defines the public contract exposed by the Indexing
Platform.

Current MVP:
    - Vector indexing

Future:
    - BM25 indexing
    - Knowledge Graph indexing
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.ai.knowledge.indexing.models import (
    IndexingRequest,
    IndexingResult,
)


class IndexingServiceInterface(ABC):
    """
    Public contract for the Indexing Platform.

    The implementation is responsible for orchestrating one or more
    indexing technologies while remaining independent from the calling
    application.

    Current MVP:
        - Vector Store

    Future:
        - Vector Store
        - BM25
        - Knowledge Graph
    """

    @abstractmethod
    async def index(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """
        Index an embedding artifact into all configured indexes.

        Returns
        -------
        IndexingResult
            Aggregated indexing result.
        """
        raise NotImplementedError

    @abstractmethod
    async def reindex(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """
        Rebuild all configured indexes for an embedding artifact.

        Returns
        -------
        IndexingResult
            Aggregated indexing result.
        """
        raise NotImplementedError

    @abstractmethod
    async def delete(
        self,
        request: IndexingRequest,
    ) -> IndexingResult:
        """
        Remove an embedding artifact from all configured indexes.

        Returns
        -------
        IndexingResult
            Aggregated indexing result.
        """
        raise NotImplementedError
