"""
Shared `GenerationArtifact` persistence logic (Artifact Platform PRD §24).

Extracted from `GenerationService._persist_generation_artifact` so
`StreamingService` can persist the exact same artifact type from a
streamed result -- previously only `StreamArtifact` (category `STREAM`,
a thin events/timeline/metrics record with no `request`/`response`
content) got persisted for a genuinely streamed call, regardless of
`(runtime, GENERATION)` policy, because `StreamingService` never called
this logic at all. That silently meant the online-scoring job (E5,
which reads `GenerationArtifact` specifically via `GenerationArtifactReader`)
could never score any surface's real streamed traffic -- only
non-streaming answer-producing calls (e.g. Deep Research's synthesis)
ever produced one. Confirmed live, not theoretical: a real Linear
Research query through `/research/stream` showed the `(RESEARCH,
GENERATION)` policy fix alone (2026-08-12) had no effect, since that
endpoint never reaches `GenerationService.generate()`'s persistence step
at all.
"""

from __future__ import annotations

import structlog

from app.ai.artifacts.enums import ArtifactCategory, ArtifactRuntime
from app.ai.artifacts.generation.builders import GenerationArtifactBuilder
from app.ai.artifacts.generation.writers import GenerationArtifactWriter
from app.ai.artifacts.policies.service import ArtifactPolicyService
from app.ai.runtime.generation.models import GenerationRequest, GenerationResult

logger = structlog.get_logger()


async def persist_generation_artifact(
    *,
    request: GenerationRequest,
    result: GenerationResult,
    artifact_writer: GenerationArtifactWriter,
    artifact_policy_service: ArtifactPolicyService | None,
) -> None:
    """
    Best-effort (Artifact Platform PRD §24): a storage hiccup must not
    fail a generation that already succeeded -- `GenerationArtifactWriter
    .write()` itself re-raises on failure (see its own logging), so
    that's caught and downgraded to an `artifacts.generation.failed`
    event here instead of propagating.
    """

    artifact_runtime = request.artifact_runtime or ArtifactRuntime.CHAT

    if artifact_policy_service is not None and not (
        artifact_policy_service.should_persist(
            artifact_runtime,
            ArtifactCategory.GENERATION,
        )
    ):
        logger.debug(
            "artifacts.generation.skipped",
            generation_id=str(result.generation_id),
            runtime=artifact_runtime.value,
        )
        return

    try:
        artifact = GenerationArtifactBuilder().build(
            result=result,
        )

        await artifact_writer.write(
            artifact,
        )
    except Exception as exc:
        logger.warning(
            "artifacts.generation.failed",
            generation_id=str(result.generation_id),
            reason="artifact_persistence_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
