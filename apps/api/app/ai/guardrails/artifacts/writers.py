"""
Guardrail artifact writer.

Persists guardrail artifacts using the application's storage abstraction.

This class is responsible only for writing guardrail artifacts. It does
not evaluate guardrails or build artifacts.
"""

from __future__ import annotations

from io import BytesIO

import structlog
from app.ai.guardrails.artifacts.models import GuardrailArtifact
from app.ai.guardrails.models import GuardrailResult
from app.infrastructure.storage.interfaces import DocumentStorage
from pydantic import BaseModel

logger = structlog.get_logger()


class GuardrailArtifactWriter:
    """
    Persists guardrail artifacts.
    """

    def __init__(
        self,
        storage_provider: DocumentStorage,
    ) -> None:
        self._storage = storage_provider

    async def write(
        self,
        artifact: GuardrailArtifact,
    ) -> None:
        """
        Persist a guardrail artifact.

        Storage layout (PRD §16):

        guardrails/
            {run_id}/
                input.json
                retrieval.json
                generation.json
                runtime.json
                report.json

        `runtime.json` is only written when the report actually ran a
        runtime evaluation (`GuardrailReport.runtime_result` is not `None`).
        """

        base_path = f"guardrails/{artifact.run_id}"

        log = logger.bind(
            run_id=str(artifact.run_id),
            artifact_id=str(artifact.artifact_id),
            base_path=base_path,
        )

        log.debug("guardrail_artifact_writer.write.started")

        stage_results: list[tuple[str, GuardrailResult | None]] = [
            ("input", artifact.report.input_result),
            ("retrieval", artifact.report.retrieval_result),
            ("generation", artifact.report.generation_result),
            ("runtime", artifact.report.runtime_result),
        ]

        try:
            for stage_name, stage_result in stage_results:
                if stage_result is None:
                    continue

                await self._write_json(
                    key=f"{base_path}/{stage_name}.json",
                    payload=stage_result,
                )

            await self._write_json(
                key=f"{base_path}/report.json",
                payload=artifact,
            )
        except Exception as exc:
            log.exception(
                "guardrail_artifact_writer.write_failed",
                exc_type=type(exc).__name__,
            )
            raise

        log.info(
            "guardrail_artifact_writer.write.completed",
            final_action=artifact.report.final_action.value,
            blocked=artifact.report.blocked,
        )

    async def _write_json(
        self,
        *,
        key: str,
        payload: BaseModel,
    ) -> None:

        await self._storage.upload(
            key=key,
            file=BytesIO(
                payload.model_dump_json(
                    indent=2,
                    exclude_none=True,
                ).encode("utf-8")
            ),
            content_type="application/json",
        )
