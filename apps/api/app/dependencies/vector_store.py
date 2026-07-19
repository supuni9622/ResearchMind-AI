"""Vector Store Platform dependencies."""

from __future__ import annotations

from functools import lru_cache

from app.ai.knowledge.vectorstores.create import create_vectorstore_service
from app.ai.knowledge.vectorstores.service import VectorStoreService


@lru_cache
def get_vectorstore_service() -> VectorStoreService:
    """Return the singleton configured vector-store service."""

    return create_vectorstore_service()
