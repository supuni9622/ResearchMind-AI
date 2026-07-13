"""
Retrieval Platform enumerations.
"""

from __future__ import annotations

from enum import StrEnum


class RetrievalProvider(StrEnum):
    """
    Supported retrieval providers.
    """

    QDRANT = "qdrant"


class RetrievalStrategy(StrEnum):
    """
    Retrieval strategies.
    """

    DENSE = "dense"

    SPARSE = "sparse"

    HYBRID = "hybrid"

    PARENT_CHILD = "parent_child"

    QUERY_DECOMPOSITION = "query_decomposition"


class RetrievalOperation(StrEnum):
    """
    Retrieval operations.
    """

    SEARCH = "search"
