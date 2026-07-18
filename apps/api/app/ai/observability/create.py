"""
Observability Platform composition root.
"""

from __future__ import annotations

from functools import lru_cache

from app.ai.artifacts.create import (
    create_observability_artifact_writer,
    get_artifact_policy_service,
)
from app.ai.observability.service import ObservabilityService


@lru_cache
def get_observability_service() -> ObservabilityService:

    return ObservabilityService(
        artifact_writer=create_observability_artifact_writer(),
        artifact_policy_service=get_artifact_policy_service(),
    )
