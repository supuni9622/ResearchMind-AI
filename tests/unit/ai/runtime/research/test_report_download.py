from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from app.ai.runtime.research.report_download import ResearchReportDownloadService


@pytest.mark.asyncio
async def test_report_download_returns_short_lived_url_for_run_owner() -> None:
    run_id, owner_id = uuid4(), uuid4()
    runs = AsyncMock()
    runs.get_by_id_for_owner.return_value = SimpleNamespace(id=run_id)
    storage = AsyncMock()
    storage.exists.return_value = True
    storage.generate_presigned_url.return_value = "https://storage.test/final-report.pdf"

    url = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=run_id,
        owner_id=owner_id,
    )

    assert url == "https://storage.test/final-report.pdf"
    runs.get_by_id_for_owner.assert_awaited_once_with(run_id=run_id, owner_id=owner_id)
    storage.generate_presigned_url.assert_awaited_once_with(
        key=f"artifacts/research-runs/{run_id}/final-report.pdf",
        expires_in=ResearchReportDownloadService.EXPIRES_IN_SECONDS,
    )


@pytest.mark.asyncio
async def test_report_download_hides_non_owned_or_missing_reports() -> None:
    runs = AsyncMock()
    runs.get_by_id_for_owner.return_value = None
    storage = AsyncMock()

    url = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=uuid4(),
        owner_id=uuid4(),
    )

    assert url is None
    storage.exists.assert_not_awaited()
