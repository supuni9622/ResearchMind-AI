"""Durable review-decision artifacts for bounded Research Runtime repair loops."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.ai.artifacts.models import JsonDictFile
from app.ai.artifacts.writers.base import write_json_artifact
from app.ai.runtime.research.review import ResearchReview
from app.infrastructure.storage.interfaces import DocumentStorage


class ResearchReviewArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    research_run_id: UUID
    iteration: int = Field(ge=0, le=2)
    review: ResearchReview


class ResearchReviewArtifactWriter:
    """Writes every bounded review decision once, without storing draft contents."""

    def __init__(self, storage: DocumentStorage) -> None:
        self._storage = storage

    async def write(self, artifact: ResearchReviewArtifact) -> str:
        key = f"artifacts/research-runs/{artifact.research_run_id}/review-{artifact.iteration}.json"
        if await self._storage.exists(key=key):
            return key
        await write_json_artifact(
            self._storage,
            key=key,
            payload=JsonDictFile(data=artifact.model_dump(mode="json")),
        )
        return key
