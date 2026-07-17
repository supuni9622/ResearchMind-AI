from __future__ import annotations

from app.ai.runtime.generation.models import (
    GenerationResult,
)
from app.ai.runtime.generation.validation.interfaces import (
    OutputValidatorInterface,
)
from app.ai.runtime.generation.validation.models import (
    ValidationIssue,
    ValidationSeverity,
    ValidatorOutcome,
)
from app.ai.runtime.generation.validation.runtime.fields import (
    get_list_field,
    item_id,
)


class DependencyValidator(
    OutputValidatorInterface,
):
    """
    Checks that a list field of dependency-carrying items (e.g. a
    planner's `steps`) only references sibling ids that actually exist
    and forms no dependency cycle.

    Each item's own id is resolved via `id_keys`, and its dependency
    list (a list of ids, or objects carrying one under `id_keys`) is
    read from `dependency_key`. An item with no `dependency_key` value
    is treated as having no dependencies, not an error.

    Runs only when `list_field` is present as a non-empty list — an
    output with no steps has nothing to check (that's
    `CompletenessValidator`'s job).
    """

    def __init__(
        self,
        *,
        list_field: str = "steps",
        id_keys: tuple[str, ...] = (
            "id",
            "step_id",
        ),
        dependency_key: str = "depends_on",
    ) -> None:
        self._list_field = list_field

        self._id_keys = id_keys

        self._dependency_key = dependency_key

    @property
    def name(
        self,
    ) -> str:
        return "runtime_dependency"

    async def validate(
        self,
        result: GenerationResult,
    ) -> ValidatorOutcome:

        items = get_list_field(
            result.parsed_output,
            self._list_field,
        )

        if not items:
            return ValidatorOutcome()

        item_ids: list[str | None] = [item_id(item, *self._id_keys) for item in items]

        known_ids = {item_id_value for item_id_value in item_ids if item_id_value is not None}

        dependencies: dict[str, list[str]] = {}

        issues: list[ValidationIssue] = []

        for index, item in enumerate(items):
            source_id = item_ids[index]

            deps = [
                dep_id
                for dep in get_list_field(
                    item,
                    self._dependency_key,
                )
                if (dep_id := item_id(dep, *self._id_keys)) is not None
            ]

            if source_id is not None:
                dependencies[source_id] = deps

            unknown_deps = [dep for dep in deps if dep not in known_ids]

            if unknown_deps:
                issues.append(
                    ValidationIssue(
                        validator=self.name,
                        severity=ValidationSeverity.ERROR,
                        message=(
                            f"{self._list_field} item {index} depends on unknown "
                            f"id(s): {', '.join(sorted(unknown_deps))}."
                        ),
                        details={
                            "index": index,
                            "unknown_dependencies": sorted(unknown_deps),
                        },
                    )
                )

        cycle = self._find_cycle(
            dependencies,
        )

        if cycle is not None:
            issues.append(
                ValidationIssue(
                    validator=self.name,
                    severity=ValidationSeverity.ERROR,
                    message=(
                        f"{self._list_field} has a circular dependency: "
                        f"{' -> '.join([*cycle, cycle[0]])}."
                    ),
                    details={
                        "cycle": cycle,
                    },
                )
            )

        return ValidatorOutcome(
            issues=issues,
        )

    @staticmethod
    def _find_cycle(
        dependencies: dict[str, list[str]],
    ) -> list[str] | None:
        """DFS cycle detection over the id -> depends_on graph."""

        WHITE, GRAY, BLACK = 0, 1, 2

        color: dict[str, int] = dict.fromkeys(dependencies, WHITE)

        path: list[str] = []

        def visit(
            node: str,
        ) -> list[str] | None:

            color[node] = GRAY

            path.append(node)

            for neighbor in dependencies.get(node, []):
                if neighbor not in color:
                    continue

                if color[neighbor] == GRAY:
                    return path[path.index(neighbor) :]

                if color[neighbor] == WHITE:
                    found = visit(neighbor)

                    if found is not None:
                        return found

            path.pop()

            color[node] = BLACK

            return None

        for node in dependencies:
            if color[node] == WHITE:
                found = visit(node)

                if found is not None:
                    return found

        return None
