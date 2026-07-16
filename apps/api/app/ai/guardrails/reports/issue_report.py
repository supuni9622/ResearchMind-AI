from __future__ import annotations

from collections import defaultdict

from app.ai.guardrails.enums import GuardrailCategory, GuardrailSeverity
from app.ai.guardrails.models import GuardrailIssue


def group_by_severity(
    issues: list[GuardrailIssue],
) -> dict[GuardrailSeverity, list[GuardrailIssue]]:

    grouped: dict[GuardrailSeverity, list[GuardrailIssue]] = defaultdict(list)

    for issue in issues:
        grouped[issue.severity].append(issue)

    return dict(grouped)


def group_by_category(
    issues: list[GuardrailIssue],
) -> dict[GuardrailCategory, list[GuardrailIssue]]:

    grouped: dict[GuardrailCategory, list[GuardrailIssue]] = defaultdict(list)

    for issue in issues:
        grouped[issue.category].append(issue)

    return dict(grouped)


def count_by_severity(
    issues: list[GuardrailIssue],
) -> dict[GuardrailSeverity, int]:

    return {severity: len(group) for severity, group in group_by_severity(issues).items()}
