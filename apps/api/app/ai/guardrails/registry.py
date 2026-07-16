from __future__ import annotations

from app.ai.guardrails.interfaces import (
    GenerationGuardrailInterface,
    InputGuardrailInterface,
    RetrievalGuardrailInterface,
    RuntimeGuardrailInterface,
)


class GuardrailRegistry:
    """
    Dynamic guardrail registration (PRD §14).

    Groups guardrails by stage so `GuardrailService` can run each stage
    independently. A plain list under the hood — registration order is
    preserved, which is also the order checks run in and the order
    their issues appear in `GuardrailResult.issues`. Mirrors
    `ValidationRegistry`.
    """

    def __init__(
        self,
    ) -> None:
        self._input_guardrails: list[InputGuardrailInterface] = []

        self._retrieval_guardrails: list[RetrievalGuardrailInterface] = []

        self._generation_guardrails: list[GenerationGuardrailInterface] = []

        self._runtime_guardrails: list[RuntimeGuardrailInterface] = []

    # ==========================================================
    # Registration
    # ==========================================================

    def register_input_guardrail(
        self,
        guardrail: InputGuardrailInterface,
    ) -> None:
        self._input_guardrails.append(
            guardrail,
        )

    def register_retrieval_guardrail(
        self,
        guardrail: RetrievalGuardrailInterface,
    ) -> None:
        self._retrieval_guardrails.append(
            guardrail,
        )

    def register_generation_guardrail(
        self,
        guardrail: GenerationGuardrailInterface,
    ) -> None:
        self._generation_guardrails.append(
            guardrail,
        )

    def register_runtime_guardrail(
        self,
        guardrail: RuntimeGuardrailInterface,
    ) -> None:
        self._runtime_guardrails.append(
            guardrail,
        )

    # ==========================================================
    # Lookup
    # ==========================================================

    @property
    def input_guardrails(
        self,
    ) -> list[InputGuardrailInterface]:
        return list(
            self._input_guardrails,
        )

    @property
    def retrieval_guardrails(
        self,
    ) -> list[RetrievalGuardrailInterface]:
        return list(
            self._retrieval_guardrails,
        )

    @property
    def generation_guardrails(
        self,
    ) -> list[GenerationGuardrailInterface]:
        return list(
            self._generation_guardrails,
        )

    @property
    def runtime_guardrails(
        self,
    ) -> list[RuntimeGuardrailInterface]:
        return list(
            self._runtime_guardrails,
        )
