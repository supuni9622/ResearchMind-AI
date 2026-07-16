from __future__ import annotations

from typing import BinaryIO
from uuid import uuid4

from app.ai.guardrails.artifacts.builders import GuardrailArtifactBuilder
from app.ai.guardrails.artifacts.writers import GuardrailArtifactWriter
from app.ai.guardrails.enums import GuardrailAction, GuardrailStage
from app.ai.guardrails.models import GuardrailReport, GuardrailResult
from app.infrastructure.storage.interfaces import DocumentStorage


class _FakeDocumentStorage(DocumentStorage):
    def __init__(self) -> None:
        self.uploads: dict[str, bytes] = {}

    async def upload(self, *, key: str, file: BinaryIO, content_type: str) -> None:
        self.uploads[key] = file.read()

    async def download(self, *, key: str) -> bytes:
        return self.uploads[key]

    async def delete(self, *, key: str) -> None:
        del self.uploads[key]

    async def exists(self, *, key: str) -> bool:
        return key in self.uploads

    async def generate_presigned_url(self, *, key: str, expires_in: int = 3600) -> str:
        return f"https://example.test/{key}"


def _result(stage: GuardrailStage) -> GuardrailResult:
    return GuardrailResult(stage=stage, passed=True, blocked=False, action=GuardrailAction.ALLOW)


async def test_write_persists_one_file_per_stage_plus_report() -> None:
    storage = _FakeDocumentStorage()
    writer = GuardrailArtifactWriter(storage_provider=storage)

    run_id = uuid4()

    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(GuardrailStage.GENERATION),
        runtime_result=_result(GuardrailStage.RUNTIME),
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    artifact = GuardrailArtifactBuilder().build(run_id=run_id, report=report)

    await writer.write(artifact)

    assert set(storage.uploads.keys()) == {
        f"guardrails/{run_id}/input.json",
        f"guardrails/{run_id}/retrieval.json",
        f"guardrails/{run_id}/generation.json",
        f"guardrails/{run_id}/runtime.json",
        f"guardrails/{run_id}/report.json",
    }


async def test_write_skips_runtime_json_when_no_runtime_result() -> None:
    storage = _FakeDocumentStorage()
    writer = GuardrailArtifactWriter(storage_provider=storage)

    run_id = uuid4()

    report = GuardrailReport(
        input_result=_result(GuardrailStage.INPUT),
        retrieval_result=_result(GuardrailStage.RETRIEVAL),
        generation_result=_result(GuardrailStage.GENERATION),
        runtime_result=None,
        final_action=GuardrailAction.ALLOW,
        blocked=False,
    )

    artifact = GuardrailArtifactBuilder().build(run_id=run_id, report=report)

    await writer.write(artifact)

    assert set(storage.uploads.keys()) == {
        f"guardrails/{run_id}/input.json",
        f"guardrails/{run_id}/retrieval.json",
        f"guardrails/{run_id}/generation.json",
        f"guardrails/{run_id}/report.json",
    }
