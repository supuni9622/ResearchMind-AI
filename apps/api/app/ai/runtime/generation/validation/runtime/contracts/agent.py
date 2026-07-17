from __future__ import annotations

from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.runtime.contracts.base import (
    BaseRuntimeContract,
)
from app.ai.runtime.generation.validation.runtime.enums import (
    RuntimeType,
)
from app.ai.runtime.generation.validation.runtime.validators.completeness import (
    CompletenessValidator,
)

_MIN_TOOL_TRACE_ENTRIES = 1


class AgentRuntimeContract(
    BaseRuntimeContract,
):
    """
    Agent Runtime Contract — requires a non-empty `reasoning` field, a
    `completion_state` field, and at least one `tool_trace` entry
    recording what tools the agent actually invoked.

    Entirely composed from `CompletenessValidator`, same as the other
    contracts: existence of `reasoning`/`completion_state` plus a
    minimum-count check on `tool_trace` cover all three requirements
    without a bespoke check.
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "reasoning",
                    "completion_state",
                ],
                list_minimums={
                    "tool_trace": _MIN_TOOL_TRACE_ENTRIES,
                },
            ),
        ]

    @property
    def runtime(
        self,
    ) -> RuntimeType:
        return RuntimeType.AGENT

    @property
    def contract_name(
        self,
    ) -> str:
        return "agent_contract"

    @property
    def checks(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._checks,
        )
