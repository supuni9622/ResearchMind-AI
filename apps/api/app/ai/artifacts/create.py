"""
Artifact Platform composition root.

Per-category writer factories are added incrementally as each runtime
gets wired (generation/streaming/conversation) -- this module is the
single place other platforms' own `create.py` should import from.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.artifacts.conversation.writers import ConversationArtifactWriter
from app.ai.artifacts.generation.writers import GenerationArtifactWriter
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.artifacts.research.writers import ResearchArtifactWriter
from app.ai.artifacts.streaming.writers import StreamArtifactWriter
from app.core.settings import settings
from app.infrastructure.storage import create_storage
from app.infrastructure.storage.interfaces import DocumentStorage


def create_artifact_storage() -> DocumentStorage:

    return create_storage(settings)


@lru_cache
def get_artifact_policy_service() -> ArtifactPolicyService:

    return ArtifactPolicyService()


def create_generation_artifact_writer() -> GenerationArtifactWriter:

    return GenerationArtifactWriter(
        storage_provider=create_artifact_storage(),
    )


def create_stream_artifact_writer() -> StreamArtifactWriter:

    return StreamArtifactWriter(
        storage_provider=create_artifact_storage(),
    )


def create_conversation_artifact_writer() -> ConversationArtifactWriter:

    return ConversationArtifactWriter(
        storage_provider=create_artifact_storage(),
    )


def create_research_artifact_writer() -> ResearchArtifactWriter:

    return ResearchArtifactWriter(
        storage_provider=create_artifact_storage(),
    )
