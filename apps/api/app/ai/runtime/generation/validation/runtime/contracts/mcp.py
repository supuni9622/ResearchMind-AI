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
from app.ai.runtime.generation.validation.runtime.validators.consistency import (
    ConsistencyValidator,
)

_MIN_TOOL_OUTPUTS = 1


class MCPRuntimeContract(
    BaseRuntimeContract,
):
    """
    MCP Runtime Contract — requires at least one `tool_outputs` entry,
    a non-empty `execution_metadata` field, and referential integrity
    between `tool_references` and the `tool_outputs` they point at.

    Entirely composed from the generic runtime validators:
    `CompletenessValidator` covers "tool outputs valid" (existence)
    and "execution metadata valid"; `ConsistencyValidator` — reused
    with MCP's own field names rather than its `sections`/`evidence`
    defaults — covers "tool references valid".
    """

    def __init__(
        self,
    ) -> None:
        self._checks: list[OutputValidatorInterface] = [
            CompletenessValidator(
                required_fields=[
                    "execution_metadata",
                ],
                list_minimums={
                    "tool_outputs": _MIN_TOOL_OUTPUTS,
                },
            ),
            ConsistencyValidator(
                list_field="tool_outputs",
                id_keys=(
                    "id",
                    "tool_call_id",
                ),
                ref_list_field="tool_references",
                ref_key="tool_call_id",
            ),
        ]

    @property
    def runtime(
        self,
    ) -> RuntimeType:
        return RuntimeType.MCP

    @property
    def contract_name(
        self,
    ) -> str:
        return "mcp_contract"

    @property
    def checks(
        self,
    ) -> list[OutputValidatorInterface]:
        return list(
            self._checks,
        )
