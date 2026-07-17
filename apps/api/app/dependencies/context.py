"""
Context Builder platform dependencies.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.knowledge.context.create import create_context_builder
from app.ai.knowledge.context.service import ContextBuilderService


@lru_cache
def get_context_builder() -> ContextBuilderService:
    """
    Return singleton ContextBuilderService.
    """

    return create_context_builder()
