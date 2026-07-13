"""
Retrieval platform dependencies.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.knowledge.retrieval.create import (
    create_retrieval_service,
)
from app.ai.knowledge.retrieval.service import (
    RetrievalService,
)


@lru_cache
def get_retrieval_service() -> RetrievalService:
    """
    Return singleton RetrievalService.
    """

    return create_retrieval_service()
