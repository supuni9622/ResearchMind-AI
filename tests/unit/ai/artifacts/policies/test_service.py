from __future__ import annotations

from app.ai.artifacts.enums import ArtifactCategory, ArtifactPolicy, ArtifactRuntime
from app.ai.artifacts.policies.models import ArtifactPolicyRule
from app.ai.artifacts.policies.service import ArtifactPolicyService


def test_resolves_configured_rule() -> None:
    service = ArtifactPolicyService()

    assert (
        service.resolve_policy(ArtifactRuntime.CHAT, ArtifactCategory.GENERATION)
        is ArtifactPolicy.SESSION
    )
    assert (
        service.resolve_policy(ArtifactRuntime.RESEARCH, ArtifactCategory.RESEARCH)
        is ArtifactPolicy.PERMANENT
    )


def test_internal_helper_never_persists_any_category() -> None:
    service = ArtifactPolicyService()

    for category in ArtifactCategory:
        assert service.should_persist(ArtifactRuntime.INTERNAL_HELPER, category) is False


def test_unmapped_combination_fails_safe_to_never() -> None:
    service = ArtifactPolicyService()

    assert (
        service.resolve_policy(ArtifactRuntime.CHAT, ArtifactCategory.AGENT) is ArtifactPolicy.NEVER
    )
    assert service.should_persist(ArtifactRuntime.CHAT, ArtifactCategory.AGENT) is False


def test_should_persist_true_for_any_non_never_policy() -> None:
    service = ArtifactPolicyService()

    assert service.should_persist(ArtifactRuntime.CHAT, ArtifactCategory.STREAM) is True


def test_research_observability_persists_permanently() -> None:
    """
    Regression: ResearchService tags every GenerationRequest
    `artifact_runtime=ArtifactRuntime.RESEARCH` (research/service.py), so
    without an explicit (RESEARCH, OBSERVABILITY) rule this silently fell
    back to NEVER -- ObservabilityService.record_generation() would skip
    every research observability write with no error, only a debug log
    line, even with LangSmith tracing fully working.
    """

    service = ArtifactPolicyService()

    assert (
        service.resolve_policy(ArtifactRuntime.RESEARCH, ArtifactCategory.OBSERVABILITY)
        is ArtifactPolicy.PERMANENT
    )
    assert service.should_persist(ArtifactRuntime.RESEARCH, ArtifactCategory.OBSERVABILITY) is True


def test_custom_rules_override_defaults() -> None:
    service = ArtifactPolicyService(
        rules=[
            ArtifactPolicyRule(
                runtime=ArtifactRuntime.CHAT,
                category=ArtifactCategory.GENERATION,
                policy=ArtifactPolicy.NEVER,
            ),
        ]
    )

    assert service.should_persist(ArtifactRuntime.CHAT, ArtifactCategory.GENERATION) is False
