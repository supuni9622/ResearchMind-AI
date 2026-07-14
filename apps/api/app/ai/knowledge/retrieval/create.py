"""
Retrieval Platform composition root.

Assembles the Retrieval Platform by registering all retrieval providers
and constructing the RetrievalService.

This module is the single composition root for the Retrieval Platform.
"""

from __future__ import annotations

from app.ai.knowledge.cache.query_embeddings.create import (
    create_query_embedding_cache,
)
from app.ai.knowledge.embeddings.create import (
    create_embedding_registry,
)
from app.ai.knowledge.indexing.create import (
    create_sparse_embedding_provider,
)
from app.ai.knowledge.reranking.create import (
    create_reranking_service,
)
from app.ai.knowledge.retrieval.config import (
    QdrantRetrievalConfig,
)
from app.ai.knowledge.retrieval.fusion.service import (
    RetrievalFusionService,
)
from app.ai.knowledge.retrieval.interfaces import (
    RetrievalProviderInterface,
)
from app.ai.knowledge.retrieval.providers.qdrant import (
    QdrantRetrievalProvider,
)
from app.ai.knowledge.retrieval.query.dense_service import (
    QueryEmbeddingService,
)
from app.ai.knowledge.retrieval.query.sparse_service import (
    SparseQueryEmbeddingService,
)
from app.ai.knowledge.retrieval.registry import (
    RetrievalRegistry,
)
from app.ai.knowledge.retrieval.service import (
    RetrievalService,
)
from app.ai.knowledge.vectorstores.create import (
    create_qdrant_client,
)
from app.core.settings import settings


def create_retrieval_registry() -> RetrievalRegistry:
    """
    Create a fully configured RetrievalRegistry.
    """

    qdrant_client = create_qdrant_client()

    providers: list[RetrievalProviderInterface] = [
        QdrantRetrievalProvider(
            client=qdrant_client,
            config=QdrantRetrievalConfig(
                collection_name=(settings.qdrant_collection_name),
            ),
        ),
    ]

    return RetrievalRegistry(
        providers,
    )


def create_query_embedding_service() -> QueryEmbeddingService:
    """
    Create dense query embedding service.
    """

    return QueryEmbeddingService(
        registry=(create_embedding_registry()),
        cache=(create_query_embedding_cache()),
    )


def create_sparse_query_embedding_service() -> SparseQueryEmbeddingService:
    """
    Create sparse query embedding service.
    """

    return SparseQueryEmbeddingService(
        provider=(create_sparse_embedding_provider()),
    )


def create_fusion_service() -> RetrievalFusionService:
    """
    Create retrieval fusion service.

    Currently uses:

    - Reciprocal Rank Fusion (RRF)

    Future:

    - Weighted RRF
    - Relative Score Fusion
    - Score Fusion
    """

    return RetrievalFusionService()


def create_retrieval_service() -> RetrievalService:
    """
    Create a fully configured RetrievalService.
    """

    return RetrievalService(
        registry=(create_retrieval_registry()),
        query_embedding_service=(create_query_embedding_service()),
        sparse_query_embedding_service=(create_sparse_query_embedding_service()),
        fusion_service=(create_fusion_service()),
        reranking_service=(create_reranking_service()),
    )
