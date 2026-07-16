from __future__ import annotations

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.reports.issue_report import (
    count_by_severity,
    group_by_category,
    group_by_severity,
)

from tests.unit.ai.guardrails.factories import make_guardrail_issue


def test_group_by_severity() -> None:
    issues = [
        make_guardrail_issue(severity=GuardrailSeverity.WARNING),
        make_guardrail_issue(severity=GuardrailSeverity.ERROR),
        make_guardrail_issue(severity=GuardrailSeverity.WARNING),
    ]

    grouped = group_by_severity(issues)

    assert len(grouped[GuardrailSeverity.WARNING]) == 2
    assert len(grouped[GuardrailSeverity.ERROR]) == 1
    assert GuardrailSeverity.CRITICAL not in grouped


def test_group_by_category() -> None:
    issues = [
        make_guardrail_issue(category=GuardrailCategory.PII),
        make_guardrail_issue(category=GuardrailCategory.BUDGET),
    ]

    grouped = group_by_category(issues)

    assert set(grouped.keys()) == {GuardrailCategory.PII, GuardrailCategory.BUDGET}


def test_count_by_severity() -> None:
    issues = [
        make_guardrail_issue(severity=GuardrailSeverity.WARNING),
        make_guardrail_issue(severity=GuardrailSeverity.WARNING),
        make_guardrail_issue(severity=GuardrailSeverity.CRITICAL),
    ]

    counts = count_by_severity(issues)

    assert counts == {GuardrailSeverity.WARNING: 2, GuardrailSeverity.CRITICAL: 1}


def test_empty_issue_list_produces_empty_groupings() -> None:
    assert group_by_severity([]) == {}
    assert group_by_category([]) == {}
    assert count_by_severity([]) == {}
