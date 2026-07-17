"""
Unit tests for DependencyValidator.

Covers:
- A valid, acyclic dependency graph has no issues
- A step depending on an unknown id is an ERROR
- A circular dependency (direct and transitive) is an ERROR
- A step with no dependencies at all is not flagged
- Missing/empty list_field means nothing to check
- Dependencies expressed as bare string ids (not objects) resolve correctly
"""

from __future__ import annotations

from app.ai.runtime.generation.validation.models import ValidationSeverity
from app.ai.runtime.generation.validation.runtime.validators.dependency import (
    DependencyValidator,
)

from tests.unit.ai.runtime.generation.validation.factories import make_result


async def test_valid_acyclic_graph_has_no_issues() -> None:
    validator = DependencyValidator()

    result = make_result(
        parsed_output={
            "steps": [
                {"id": "step-1", "depends_on": []},
                {"id": "step-2", "depends_on": ["step-1"]},
                {"id": "step-3", "depends_on": ["step-1", "step-2"]},
            ],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_dependency_on_unknown_id_is_an_error() -> None:
    validator = DependencyValidator()

    result = make_result(
        parsed_output={
            "steps": [
                {"id": "step-1", "depends_on": ["step-does-not-exist"]},
            ],
        }
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert outcome.issues[0].severity == ValidationSeverity.ERROR
    assert "step-does-not-exist" in outcome.issues[0].message


async def test_direct_circular_dependency_is_an_error() -> None:
    validator = DependencyValidator()

    result = make_result(
        parsed_output={
            "steps": [
                {"id": "step-1", "depends_on": ["step-2"]},
                {"id": "step-2", "depends_on": ["step-1"]},
            ],
        }
    )

    outcome = await validator.validate(result)

    cycle_issues = [issue for issue in outcome.issues if "circular" in issue.message]

    assert len(cycle_issues) == 1
    assert cycle_issues[0].severity == ValidationSeverity.ERROR


async def test_transitive_circular_dependency_is_an_error() -> None:
    validator = DependencyValidator()

    result = make_result(
        parsed_output={
            "steps": [
                {"id": "step-1", "depends_on": ["step-2"]},
                {"id": "step-2", "depends_on": ["step-3"]},
                {"id": "step-3", "depends_on": ["step-1"]},
            ],
        }
    )

    outcome = await validator.validate(result)

    assert any("circular" in issue.message for issue in outcome.issues)


async def test_step_with_no_dependencies_is_not_flagged() -> None:
    validator = DependencyValidator()

    result = make_result(
        parsed_output={
            "steps": [
                {"id": "step-1"},
            ],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_missing_list_field_means_nothing_to_check() -> None:
    validator = DependencyValidator()

    result = make_result(parsed_output={})

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_bare_string_dependency_ids_resolve() -> None:
    validator = DependencyValidator()

    result = make_result(
        parsed_output={
            "steps": [
                {"id": "step-1", "depends_on": []},
                {"id": "step-2", "depends_on": ["step-1"]},
            ],
        }
    )

    outcome = await validator.validate(result)

    assert outcome.issues == []


async def test_custom_field_names_are_respected() -> None:
    validator = DependencyValidator(
        list_field="tasks",
        id_keys=("task_id",),
        dependency_key="requires",
    )

    result = make_result(
        parsed_output={
            "tasks": [
                {"task_id": "t1", "requires": ["t2"]},
            ],
        }
    )

    outcome = await validator.validate(result)

    assert len(outcome.issues) == 1
    assert "t2" in outcome.issues[0].message
