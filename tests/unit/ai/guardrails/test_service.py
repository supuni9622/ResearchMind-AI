"""
Unit tests for GuardrailService.

Covers:
- evaluate_input/retrieval/generation/runtime aggregate issues and stamp
  the right GuardrailStage onto each one
- a crashing guardrail becomes a WARNING "guardrail_crashed" issue rather
  than propagating, and doesn't stop the remaining guardrails
- FailPolicy.FAIL_CLOSED escalates a crash to blocking; FAIL_OPEN (default)
  does not
- RegenerationPolicy/RuntimePolicy drive REGENERATE/BLOCK action derivation
- retrieval's optional check_citations() seam is only invoked when
  citations are supplied
- evaluate() builds a full report with the highest-precedence final_action
  across every stage that ran
- guardrail_names lists every registered check across all four stages
"""

from __future__ import annotations

from app.ai.guardrails.enums import (
    GuardrailAction,
    GuardrailCategory,
    GuardrailSeverity,
    GuardrailStage,
)
from app.ai.guardrails.interfaces import (
    GenerationGuardrailInterface,
    InputGuardrailInterface,
    RetrievalGuardrailInterface,
    RuntimeGuardrailInterface,
)
from app.ai.guardrails.models import GuardrailIssue
from app.ai.guardrails.policies.fail_policy import FailPolicy
from app.ai.guardrails.registry import GuardrailRegistry
from app.ai.guardrails.runtime.execution_limits import BudgetPolicy, ExecutionState
from app.ai.guardrails.service import GuardrailService
from app.ai.knowledge.context.citations.models import Citation
from app.ai.knowledge.context.models import ContextChunk
from app.ai.runtime.generation.models import GenerationRequest, GenerationResult

from tests.unit.ai.guardrails.factories import (
    make_budget_policy,
    make_chunk,
    make_citation,
    make_execution_state,
    make_request,
    make_result,
)


def _issue(
    *,
    severity: GuardrailSeverity = GuardrailSeverity.WARNING,
    category: GuardrailCategory = GuardrailCategory.PROMPT_INJECTION,
    code: str = "issue",
) -> GuardrailIssue:
    return GuardrailIssue(code=code, severity=severity, category=category, message=code)


class _FakeInputGuardrail(InputGuardrailInterface):
    def __init__(self, name: str, issues: list[GuardrailIssue] | None = None, raises: bool = False):
        self._name = name
        self._issues = issues or []
        self._raises = raises

    @property
    def name(self) -> str:
        return self._name

    async def check(self, request: GenerationRequest) -> list[GuardrailIssue]:
        if self._raises:
            raise RuntimeError("boom")
        return self._issues


class _FakeRetrievalGuardrail(RetrievalGuardrailInterface):
    def __init__(
        self,
        name: str,
        issues: list[GuardrailIssue] | None = None,
        citation_issues: list[GuardrailIssue] | None = None,
        supports_citations: bool = False,
    ):
        self._name = name
        self._issues = issues or []
        self._citation_issues = citation_issues or []
        self.citation_calls = 0

        if supports_citations:
            self.check_citations = self._check_citations

    @property
    def name(self) -> str:
        return self._name

    async def check(self, chunks: list[ContextChunk]) -> list[GuardrailIssue]:
        return self._issues

    async def _check_citations(
        self, *, chunks: list[ContextChunk], citations: list[Citation]
    ) -> list[GuardrailIssue]:
        self.citation_calls += 1
        return self._citation_issues


class _FakeGenerationGuardrail(GenerationGuardrailInterface):
    def __init__(self, name: str, issues: list[GuardrailIssue] | None = None):
        self._name = name
        self._issues = issues or []

    @property
    def name(self) -> str:
        return self._name

    async def check(self, result: GenerationResult) -> list[GuardrailIssue]:
        return self._issues


class _FakeRuntimeGuardrail(RuntimeGuardrailInterface):
    def __init__(self, name: str, issues: list[GuardrailIssue] | None = None):
        self._name = name
        self._issues = issues or []

    @property
    def name(self) -> str:
        return self._name

    async def check(self, state: ExecutionState, policy: BudgetPolicy) -> list[GuardrailIssue]:
        return self._issues


async def test_evaluate_input_aggregates_and_stamps_stage() -> None:
    registry = GuardrailRegistry()
    registry.register_input_guardrail(_FakeInputGuardrail("a", [_issue()]))

    service = GuardrailService(registry=registry)

    result = await service.evaluate_input(make_request())

    assert result.passed is True
    assert len(result.issues) == 1
    assert result.issues[0].stage == GuardrailStage.INPUT


async def test_crashing_guardrail_becomes_warning_and_others_still_run() -> None:
    registry = GuardrailRegistry()
    registry.register_input_guardrail(_FakeInputGuardrail("crasher", raises=True))
    registry.register_input_guardrail(_FakeInputGuardrail("b", [_issue()]))

    service = GuardrailService(registry=registry)

    result = await service.evaluate_input(make_request())

    assert len(result.issues) == 2
    crash_issue = next(i for i in result.issues if i.code == "guardrail_crashed")
    assert crash_issue.severity == GuardrailSeverity.WARNING
    assert crash_issue.category == GuardrailCategory.SYSTEM
    assert result.blocked is False  # FAIL_OPEN default — a crash alone doesn't block


async def test_fail_closed_crash_blocks_the_stage() -> None:
    registry = GuardrailRegistry()
    registry.register_input_guardrail(_FakeInputGuardrail("crasher", raises=True))

    service = GuardrailService(registry=registry, fail_policy=FailPolicy.FAIL_CLOSED)

    result = await service.evaluate_input(make_request())

    assert result.blocked is True
    assert result.action == GuardrailAction.BLOCK


async def test_evaluate_retrieval_only_calls_check_citations_when_citations_given() -> None:
    guardrail = _FakeRetrievalGuardrail(
        "citation_check",
        citation_issues=[_issue(category=GuardrailCategory.CITATION_INTEGRITY)],
        supports_citations=True,
    )
    registry = GuardrailRegistry()
    registry.register_retrieval_guardrail(guardrail)

    service = GuardrailService(registry=registry)

    chunks = [make_chunk()]

    result_without_citations = await service.evaluate_retrieval(chunks)
    assert guardrail.citation_calls == 0
    assert result_without_citations.issues == []

    result_with_citations = await service.evaluate_retrieval(chunks, [make_citation()])
    assert guardrail.citation_calls == 1
    assert len(result_with_citations.issues) == 1


async def test_generation_faithfulness_error_triggers_regenerate_by_default() -> None:
    registry = GuardrailRegistry()
    registry.register_generation_guardrail(
        _FakeGenerationGuardrail(
            "faithfulness",
            [_issue(severity=GuardrailSeverity.ERROR, category=GuardrailCategory.FAITHFULNESS)],
        )
    )

    service = GuardrailService(registry=registry)

    result = await service.evaluate_generation(make_result())

    assert result.action == GuardrailAction.REGENERATE
    assert result.passed is False


async def test_runtime_budget_error_blocks_by_default() -> None:
    registry = GuardrailRegistry()
    registry.register_runtime_guardrail(
        _FakeRuntimeGuardrail(
            "budget", [_issue(severity=GuardrailSeverity.ERROR, category=GuardrailCategory.BUDGET)]
        )
    )

    service = GuardrailService(registry=registry)

    result = await service.evaluate_runtime(make_execution_state(), make_budget_policy())

    assert result.action == GuardrailAction.BLOCK
    assert result.blocked is True


async def test_evaluate_builds_report_with_highest_precedence_final_action() -> None:
    registry = GuardrailRegistry()
    registry.register_input_guardrail(_FakeInputGuardrail("in", [_issue()]))  # WARN
    registry.register_generation_guardrail(
        _FakeGenerationGuardrail(
            "faithfulness",
            [_issue(severity=GuardrailSeverity.ERROR, category=GuardrailCategory.FAITHFULNESS)],
        )
    )  # REGENERATE
    registry.register_runtime_guardrail(
        _FakeRuntimeGuardrail(
            "budget", [_issue(severity=GuardrailSeverity.ERROR, category=GuardrailCategory.BUDGET)]
        )
    )  # BLOCK

    service = GuardrailService(registry=registry)

    request = make_request()
    result = make_result(request=request)

    report = await service.evaluate(
        request=request,
        chunks=[],
        result=result,
        execution_state=make_execution_state(),
        budget_policy=make_budget_policy(),
    )

    assert report.final_action == GuardrailAction.BLOCK  # BLOCK outranks REGENERATE/WARN
    assert report.blocked is True
    assert report.overall_risk is not None
    assert len(report.issues) == 3


async def test_evaluate_omits_runtime_result_when_no_execution_state_given() -> None:
    registry = GuardrailRegistry()
    service = GuardrailService(registry=registry)

    request = make_request()
    report = await service.evaluate(request=request, chunks=[], result=make_result(request=request))

    assert report.runtime_result is None
    assert report.final_action == GuardrailAction.ALLOW
    assert report.blocked is False


async def test_guardrail_names_lists_every_stage() -> None:
    registry = GuardrailRegistry()
    registry.register_input_guardrail(_FakeInputGuardrail("in"))
    registry.register_retrieval_guardrail(_FakeRetrievalGuardrail("ret"))
    registry.register_generation_guardrail(_FakeGenerationGuardrail("gen"))
    registry.register_runtime_guardrail(_FakeRuntimeGuardrail("run"))

    service = GuardrailService(registry=registry)

    assert service.guardrail_names == ["in", "ret", "gen", "run"]
