"""
Query embedding cache composition root.
"""

from __future__ import annotations

from app.ai.knowledge.cache.query_embeddings.interfaces import (
    QueryEmbeddingCache,
)
from app.ai.knowledge.cache.query_embeddings.memory import (
    InMemoryQueryEmbeddingCache,
)


def create_query_embedding_cache() -> QueryEmbeddingCache:
    """
    Create query embedding cache.

    Future:

    - Redis
    - Disk cache
    - Distributed cache
    """

    return InMemoryQueryEmbeddingCache()
