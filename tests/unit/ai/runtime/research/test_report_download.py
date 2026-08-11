import json
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
    # PDF exists (gates the download itself); JSON artifact doesn't --
    # generation_id unavailable, but that must not block the PDF URL.
    storage.exists.side_effect = lambda *, key: key.endswith(".pdf")
    storage.generate_presigned_url.return_value = "https://storage.test/final-report.pdf"

    download = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=run_id,
        owner_id=owner_id,
    )

    assert download is not None
    assert download.download_url == "https://storage.test/final-report.pdf"
    assert download.generation_id is None
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

    download = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=uuid4(),
        owner_id=uuid4(),
    )

    assert download is None
    storage.exists.assert_not_awaited()


@pytest.mark.asyncio
async def test_report_download_surfaces_generation_id_from_the_json_artifact() -> None:
    """
    E21: the JSON artifact alongside the PDF carries the synthesis call's
    generation_id (persisted via ResearchDraft.generation_id) -- read it
    back so the frontend can submit POST /feedback against it.

    The mock payload is wrapped in `{"data": {...}}`, matching what
    `ResearchFinalReportArtifactWriter` actually writes via
    `write_json_artifact(payload=JsonDictFile(data=...))` -- a real bug
    (found live 2026-08-11: a completed Deep Research run's feedback
    control never rendered) was `_read_generation_id` validating the raw
    payload directly, without unwrapping `data` first, which always threw
    (silently, into the except-and-return-None branch) against every real
    artifact ever written. This test previously mocked the unwrapped
    shape and so never caught it.
    """

    run_id, owner_id = uuid4(), uuid4()
    generation_id = uuid4()
    runs = AsyncMock()
    runs.get_by_id_for_owner.return_value = SimpleNamespace(id=run_id)

    storage = AsyncMock()
    storage.exists.return_value = True
    storage.generate_presigned_url.return_value = "https://storage.test/final-report.pdf"
    storage.download.return_value = json.dumps(
        {
            "data": {
                "schema_version": 1,
                "research_run_id": str(run_id),
                "draft": {
                    "schema_version": 1,
                    "title": "t",
                    "abstract": "a",
                    "methodology": "m",
                    "findings": [{"heading": "h", "content": "c", "citation_ids": []}],
                    "discussion": "d",
                    "conclusion": "c",
                    "citation_ids": [],
                    "limitations": [],
                    "generation_id": str(generation_id),
                },
                "review": {
                    "decision": "pass",
                    "citation_integrity_score": 1.0,
                    "completeness_score": 1.0,
                    "model_quality_score": 1.0,
                    "limitations": [],
                    "gap_questions": [],
                },
            }
        }
    ).encode("utf-8")

    download = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=run_id,
        owner_id=owner_id,
    )

    assert download is not None
    assert download.generation_id == generation_id


@pytest.mark.asyncio
async def test_report_download_swallows_a_corrupt_json_artifact_without_failing() -> None:
    run_id, owner_id = uuid4(), uuid4()
    runs = AsyncMock()
    runs.get_by_id_for_owner.return_value = SimpleNamespace(id=run_id)

    storage = AsyncMock()
    storage.exists.return_value = True
    storage.generate_presigned_url.return_value = "https://storage.test/final-report.pdf"
    storage.download.return_value = b"not valid json"

    download = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=run_id,
        owner_id=owner_id,
    )

    assert download is not None
    assert download.download_url == "https://storage.test/final-report.pdf"
    assert download.generation_id is None


@pytest.mark.asyncio
async def test_report_download_swallows_a_json_artifact_missing_the_data_wrapper() -> None:
    """
    Valid JSON that isn't wrapped in `{"data": {...}}` (e.g. hand-crafted
    test fixtures, or some future writer regression) must degrade the same
    way a corrupt artifact does -- missing `generation_id`, not a 500 --
    since this method must never block the PDF download it decorates.
    """

    run_id, owner_id = uuid4(), uuid4()
    runs = AsyncMock()
    runs.get_by_id_for_owner.return_value = SimpleNamespace(id=run_id)

    storage = AsyncMock()
    storage.exists.return_value = True
    storage.generate_presigned_url.return_value = "https://storage.test/final-report.pdf"
    storage.download.return_value = json.dumps({"schema_version": 1}).encode("utf-8")

    download = await ResearchReportDownloadService(runs=runs, storage=storage).get_download_url(
        research_run_id=run_id,
        owner_id=owner_id,
    )

    assert download is not None
    assert download.generation_id is None
