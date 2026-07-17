"""
Unit tests for GenerationRuntime (the Generation Runtime Platform's
orchestrator).

Covers:
- execute() delegates to GenerationService.generate() with the same request
- execute() returns exactly what GenerationService.generate() returned
- execute() re-raises a GenerationService failure unchanged
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.ai.runtime.generation.enums import GenerationProvider
from app.ai.runtime.generation.exceptions import (
    GenerationExecutionError,
)
from app.ai.runtime.generation.orchestration.orchestrator import GenerationRuntime

from tests.unit.ai.runtime.generation.orchestration.factories import (
    make_request,
    make_result,
)


def _make_service(
    *,
    result=None,
    error: Exception | None = None,
) -> AsyncMock:
    service = AsyncMock()

    if error is not None:
        service.generate = AsyncMock(side_effect=error)
    else:
        service.generate = AsyncMock(return_value=result)

    return service


async def test_execute_delegates_to_generation_service() -> None:
    request = make_request()

    result = make_result(request=request)

    service = _make_service(result=result)

    runtime = GenerationRuntime(generation_service=service)

    returned = await runtime.execute(request)

    assert returned is result

    service.generate.assert_awaited_once_with(request=request, provider=None)


async def test_execute_forwards_an_explicit_provider_override() -> None:
    request = make_request()

    result = make_result(request=request)

    service = _make_service(result=result)

    runtime = GenerationRuntime(generation_service=service)

    await runtime.execute(request, provider=GenerationProvider.CLAUDE)

    service.generate.assert_awaited_once_with(
        request=request,
        provider=GenerationProvider.CLAUDE,
    )


async def test_execute_reraises_generation_service_failures() -> None:
    request = make_request()

    error = GenerationExecutionError("provider down")

    service = _make_service(error=error)

    runtime = GenerationRuntime(generation_service=service)

    with pytest.raises(GenerationExecutionError) as excinfo:
        await runtime.execute(request)

    assert excinfo.value is error
