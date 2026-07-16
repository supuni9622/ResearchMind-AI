"""
Guardrail artifact builder.

Builds the canonical GuardrailArtifact from a GuardrailReport. Pure —
no knowledge of storage or serialization.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.guardrails.artifacts.models import GuardrailArtifact
from app.ai.guardrails.models import GuardrailReport


class GuardrailArtifactBuilder:
    """
    Builds the canonical GuardrailArtifact.
    """

    def build(
        self,
        *,
        run_id: UUID,
        report: GuardrailReport,
    ) -> GuardrailArtifact:

        return GuardrailArtifact(
            run_id=run_id,
            report=report,
        )
