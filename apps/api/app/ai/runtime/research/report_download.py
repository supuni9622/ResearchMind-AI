"""Owner-scoped authorization for final Research Runtime report downloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID

import structlog

from app.ai.runtime.research.report_artifact import ResearchFinalReportArtifact
from app.infrastructure.storage.interfaces import DocumentStorage
from app.repositories.generation_usage import GenerationUsageRepository
from app.repositories.research_run import ResearchRunRepository

logger = structlog.get_logger()


@dataclass(frozen=True)
class ResearchReportDownload:
    download_url: str
    generation_id: UUID | None
    memory_used: bool = False


class ResearchReportDownloadService:
    """Returns an owner-authorized PDF URL, valid for EXPIRES_IN_SECONDS."""

    EXPIRES_IN_SECONDS = 30 * 24 * 60 * 60  # 30 days

    def __init__(
        self,
        *,
        runs: ResearchRunRepository,
        generation_usage: GenerationUsageRepository | None = None,
        storage: DocumentStorage,
    ) -> None:
        self._runs = runs
        self._generation_usage = generation_usage
        self._storage = storage

    async def get_download_url(
        self, *, research_run_id: UUID, owner_id: UUID
    ) -> ResearchReportDownload | None:
        run = await self._runs.get_by_id_for_owner(run_id=research_run_id, owner_id=owner_id)
        if run is None:
            return None
        key = f"artifacts/research-runs/{research_run_id}/final-report.pdf"
        if not await self._storage.exists(key=key):
            return None
        download_url = await self._storage.generate_presigned_url(
            key=key,
            expires_in=self.EXPIRES_IN_SECONDS,
        )
        generation_id = await self._read_generation_id(research_run_id)
        generation = (
            await self._generation_usage.get_owned_generation(
                owner_id=owner_id, generation_id=generation_id
            )
            if generation_id is not None and self._generation_usage is not None
            else None
        )
        return ResearchReportDownload(
            download_url=download_url,
            generation_id=generation_id,
            memory_used=bool(generation and generation.injected_memory_ids),
        )

    async def _read_generation_id(self, research_run_id: UUID) -> UUID | None:
        """
        Best-effort (E21): reads the persisted final-report.json artifact
        purely to surface `generation_id` for `POST /feedback` -- a
        missing/corrupt/pre-existing-schema artifact must never break the
        PDF download itself, which is the primary thing this endpoint is
        for.
        """

        key = f"artifacts/research-runs/{research_run_id}/final-report.json"
        try:
            if not await self._storage.exists(key=key):
                return None
            raw = await self._storage.download(key=key)
            # `ResearchFinalReportArtifactWriter` writes this via
            # `write_json_artifact`, which wraps the payload in
            # `JsonDictFile(data=...)` -- the file on disk is
            # `{"data": {...actual artifact fields...}}`, not the artifact
            # fields at the top level. Real bug found live (2026-08-11): a
            # completed Deep Research run's feedback control never
            # rendered because this always threw (caught below, logged,
            # silently returned None) on the un-unwrapped payload.
            payload = json.loads(raw)
            artifact = ResearchFinalReportArtifact.model_validate(payload["data"])
            return artifact.draft.generation_id
        except Exception:
            logger.warning(
                "research.report_download.generation_id_unavailable",
                research_run_id=str(research_run_id),
                exc_info=True,
            )
            return None
