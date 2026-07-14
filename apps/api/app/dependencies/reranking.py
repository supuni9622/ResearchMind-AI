from functools import lru_cache

from app.ai.knowledge.reranking.create import (
    create_reranking_service,
)
from app.ai.knowledge.reranking.service import (
    RerankingService,
)


@lru_cache
def get_reranking_service() -> RerankingService:
    """
    Resolve reranking service.
    """

    return create_reranking_service()
