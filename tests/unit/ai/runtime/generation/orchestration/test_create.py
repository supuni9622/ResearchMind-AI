"""
Unit tests for the Generation Runtime Platform composition root.

Covers:
- execute_generation() delegates to get_generation_runtime().execute()

`create_generation_runtime()`/`get_generation_runtime()` themselves are
not exercised here -- like `create_generation_service()`
(generation/create.py), they build the real provider registry and every
collaborator service, which requires live provider credentials/settings
this test environment doesn't have. Same scope decision as this
codebase's other heavy composition roots (see generation/create.py,
which has no test_create.py of its own either).
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.ai.runtime.generation.orchestration import create as create_module

from tests.unit.ai.runtime.generation.orchestration.factories import (
    make_request,
    make_result,
)


async def test_execute_generation_delegates_to_the_runtime_singleton(
    monkeypatch,
) -> None:
    request = make_request()

    result = make_result(request=request)

    fake_runtime = AsyncMock()

    fake_runtime.execute = AsyncMock(return_value=result)

    monkeypatch.setattr(
        create_module,
        "get_generation_runtime",
        lambda: fake_runtime,
    )

    returned = await create_module.execute_generation(request)

    assert returned is result

    fake_runtime.execute.assert_awaited_once_with(request, provider=None)
