from __future__ import annotations

from app.ai.artifacts.enums import ArtifactCategory, ArtifactPolicy, ArtifactRuntime
from app.ai.artifacts.policies.models import (
    DEFAULT_ARTIFACT_POLICY_RULES,
    ArtifactPolicyRule,
)


class ArtifactPolicyService:
    """
    Resolves whether a given runtime/category combination should be
    persisted (PRD §8). Unknown combinations fail safe to
    `ArtifactPolicy.NEVER` -- an unrecognized runtime should never
    silently start persisting artifacts.
    """

    def __init__(
        self,
        rules: list[ArtifactPolicyRule] | None = None,
    ) -> None:
        self._rules: dict[tuple[ArtifactRuntime, ArtifactCategory], ArtifactPolicy] = {
            (rule.runtime, rule.category): rule.policy
            for rule in (rules if rules is not None else DEFAULT_ARTIFACT_POLICY_RULES)
        }

    def resolve_policy(
        self,
        runtime: ArtifactRuntime,
        category: ArtifactCategory,
    ) -> ArtifactPolicy:

        return self._rules.get(
            (runtime, category),
            ArtifactPolicy.NEVER,
        )

    def should_persist(
        self,
        runtime: ArtifactRuntime,
        execution_type: ArtifactCategory,
    ) -> bool:

        return self.resolve_policy(runtime, execution_type) is not ArtifactPolicy.NEVER
