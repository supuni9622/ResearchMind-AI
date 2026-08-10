"""Owner-scoped authorization for final Research Runtime report downloads."""

from __future__ import annotations

from uuid import UUID

from app.infrastructure.storage.interfaces import DocumentStorage
from app.repositories.research_run import ResearchRunRepository


class ResearchReportDownloadService:
    """Returns an owner-authorized PDF URL, valid for EXPIRES_IN_SECONDS."""

    EXPIRES_IN_SECONDS = 30 * 24 * 60 * 60  # 30 days

    def __init__(self, *, runs: ResearchRunRepository, storage: DocumentStorage) -> None:
        self._runs = runs
        self._storage = storage

    async def get_download_url(self, *, research_run_id: UUID, owner_id: UUID) -> str | None:
        run = await self._runs.get_by_id_for_owner(run_id=research_run_id, owner_id=owner_id)
        if run is None:
            return None
        key = f"artifacts/research-runs/{research_run_id}/final-report.pdf"
        if not await self._storage.exists(key=key):
            return None
        return await self._storage.generate_presigned_url(
            key=key,
            expires_in=self.EXPIRES_IN_SECONDS,
        )
