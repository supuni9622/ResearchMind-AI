from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.ai.artifacts.enums import ArtifactCategory, ArtifactPolicy, ArtifactRuntime


class ArtifactPolicyRule(BaseModel):
    """
    A single `(runtime, category) -> policy` mapping (PRD §8).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime: ArtifactRuntime

    category: ArtifactCategory

    policy: ArtifactPolicy


#
# PRD §8's example policy table. Internal helper calls never persist,
# regardless of category. Research/Benchmark/Evaluation are canonical
# (Category 1, PRD §7) and always permanent. Chat is Category 2
# (persist per policy) -- session-scoped for its live artifact
# categories. Agent is long-term, matching its "Future Runtime
# Foundation" framing (PRD §18) once an Agent Runtime exists.
#
DEFAULT_ARTIFACT_POLICY_RULES: list[ArtifactPolicyRule] = [
    *(
        ArtifactPolicyRule(
            runtime=ArtifactRuntime.INTERNAL_HELPER,
            category=category,
            policy=ArtifactPolicy.NEVER,
        )
        for category in ArtifactCategory
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.CHAT,
        category=ArtifactCategory.GENERATION,
        policy=ArtifactPolicy.SESSION,
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.CHAT,
        category=ArtifactCategory.STREAM,
        policy=ArtifactPolicy.SESSION,
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.CHAT,
        category=ArtifactCategory.CONVERSATION,
        policy=ArtifactPolicy.SESSION,
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.RESEARCH,
        category=ArtifactCategory.RESEARCH,
        policy=ArtifactPolicy.PERMANENT,
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.AGENT,
        category=ArtifactCategory.AGENT,
        policy=ArtifactPolicy.LONG_TERM,
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.BENCHMARK,
        category=ArtifactCategory.EVALUATION,
        policy=ArtifactPolicy.PERMANENT,
    ),
    ArtifactPolicyRule(
        runtime=ArtifactRuntime.EVALUATION,
        category=ArtifactCategory.EVALUATION,
        policy=ArtifactPolicy.PERMANENT,
    ),
]
