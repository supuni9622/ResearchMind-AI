from __future__ import annotations

from enum import StrEnum


class ArtifactPolicy(StrEnum):
    """
    How long a category of artifact should be retained (PRD §8).

    `NEVER` means "do not persist at all" -- `ArtifactPolicyService.
    should_persist()` treats this as the only false-y policy value.
    """

    NEVER = "never"

    SESSION = "session"

    SHORT_TERM = "short_term"

    LONG_TERM = "long_term"

    PERMANENT = "permanent"


class ArtifactCategory(StrEnum):
    """
    Which kind of artifact is being persisted -- mirrors the S3 prefixes
    in PRD §12 (`artifacts/{category}/...`).
    """

    GENERATION = "generations"

    STREAM = "streams"

    CONVERSATION = "conversations"

    SESSION = "sessions"

    RESEARCH = "research"

    AGENT = "agents"

    EVALUATION = "evaluations"

    OBSERVABILITY = "observability"


class ArtifactRuntime(StrEnum):
    """
    Which runtime is issuing the execution being considered for
    persistence, for `ArtifactPolicyService` lookups (PRD §8).

    Distinct from `caching.enums.CacheRuntime` and `validation.runtime.
    enums.RuntimeType` -- this codebase's established convention is that
    each platform owns its own runtime concept rather than sharing one
    (see the Runtime Caching and Runtime Validation platforms), since the
    policy dimensions they each key on don't line up 1:1.
    """

    INTERNAL_HELPER = "internal_helper"

    CHAT = "chat"

    RESEARCH = "research"

    AGENT = "agent"

    BENCHMARK = "benchmark"

    EVALUATION = "evaluation"

    PROCESSING = "processing"
