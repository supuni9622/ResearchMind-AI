from __future__ import annotations

from app.ai.guardrails.models import GuardrailReport, GuardrailResult


def summarize_report(
    report: GuardrailReport,
) -> str:
    """One-line human-readable summary of a full guardrail report."""

    if report.blocked:
        blocking_stages = ", ".join(
            name for name, result in _named_stages(report) if result.blocked
        )

        return (
            f"BLOCKED ({blocking_stages}): {len(report.issues)} issue(s), "
            f"overall_risk={_format_risk(report.overall_risk)}"
        )

    if not report.issues:
        return f"ALLOWED: no issues across {_stage_count(report)} stage(s)."

    return (
        f"{report.final_action.value.upper()}: {len(report.issues)} issue(s), "
        f"overall_risk={_format_risk(report.overall_risk)}"
    )


def stage_summaries(
    report: GuardrailReport,
) -> dict[str, str]:
    """Per-stage one-line summaries, keyed by stage name."""

    return {name: _summarize_stage(result) for name, result in _named_stages(report)}


def _summarize_stage(
    result: GuardrailResult,
) -> str:

    if not result.issues:
        return "ALLOWED: no issues."

    return f"{result.action.value.upper()}: {len(result.issues)} issue(s)."


def _named_stages(
    report: GuardrailReport,
) -> list[tuple[str, GuardrailResult]]:

    stages = [
        ("input", report.input_result),
        ("retrieval", report.retrieval_result),
        ("generation", report.generation_result),
    ]

    if report.runtime_result is not None:
        stages.append(("runtime", report.runtime_result))

    return stages


def _stage_count(
    report: GuardrailReport,
) -> int:

    return len(_named_stages(report))


def _format_risk(
    risk: float | None,
) -> str:

    return f"{risk:.2f}" if risk is not None else "n/a"
