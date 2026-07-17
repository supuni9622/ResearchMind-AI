"""
Generation / Streaming platform dependencies.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.artifacts.conversation.writers import (
    ConversationArtifactWriter,
)
from app.ai.artifacts.create import (
    create_conversation_artifact_writer,
    get_artifact_policy_service,
)
from app.ai.artifacts.policies.service import (
    ArtifactPolicyService,
)
from app.ai.runtime.generation.create import (
    create_generation_service,
)
from app.ai.runtime.generation.service import (
    GenerationService,
)
from app.ai.runtime.generation.streaming.create import (
    create_streaming_service,
)
from app.ai.runtime.generation.streaming.service import (
    StreamingService,
)
from app.db.session import get_db
from app.services.conversation import ConversationService


@lru_cache
def get_generation_service() -> GenerationService:
    """
    Return singleton GenerationService.
    """

    return create_generation_service()


@lru_cache
def get_streaming_service() -> StreamingService:
    """
    Return singleton StreamingService.
    """

    return create_streaming_service()


@lru_cache
def get_conversation_artifact_writer() -> ConversationArtifactWriter:
    """
    Return singleton ConversationArtifactWriter -- stateless (S3-backed),
    unlike `ConversationService` below which carries per-request DB
    session state and can't be cached.
    """

    return create_conversation_artifact_writer()


@lru_cache
def get_artifact_policy_service_dependency() -> ArtifactPolicyService:
    """
    Thin FastAPI-`Depends`-compatible wrapper around the Artifact
    Platform's own `get_artifact_policy_service()` composition root.
    """

    return get_artifact_policy_service()


def get_conversation_service(
    session: AsyncSession = Depends(get_db),
) -> ConversationService:
    """
    Return a request-scoped ConversationService bound to this request's
    database session (unlike the singletons above, this one carries
    per-request state and can't be cached).
    """

    return ConversationService(session)
