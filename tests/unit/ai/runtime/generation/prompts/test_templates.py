"""
Integration-style tests that render every registered prompt template
end to end.

Covers:
- Every template under templates/ builds and renders successfully with
  dummy values for its own extracted variables, with no missing-variable
  error.

Iterates: research/v1, research/v2, chat/v1, chat/v2, chat/v3,
summary/v1, summary/v2 -- this is the guard that catches a broken
prompt.md or metadata.yaml file immediately, before it reaches a real
generation request.

TokenCounter is injected as a fake: the real implementation dials out
to Anthropic/Gemini for some providers, which has no place in this
offline, template-integrity sweep.
"""

from __future__ import annotations

import pytest
from app.ai.runtime.generation.prompts.models import PromptRenderRequest
from app.ai.runtime.generation.prompts.registry import PromptRegistry
from app.ai.runtime.generation.prompts.service import PromptService

from tests.unit.ai.runtime.generation.prompts.factories import TEMPLATES_ROOT, make_token_counter

ALL_TEMPLATES = [
    ("research", "v1"),
    ("research", "v2"),
    ("chat", "v1"),
    ("chat", "v2"),
    ("chat", "v3"),
    ("summary", "v1"),
    ("summary", "v2"),
]


@pytest.fixture(scope="module")
def service() -> PromptService:
    registry = PromptRegistry()
    registry.register_all(TEMPLATES_ROOT)
    return PromptService(registry, make_token_counter())


def test_all_expected_templates_are_registered(service: PromptService) -> None:
    for name, version in ALL_TEMPLATES:
        assert service.exists(name, version), f"missing template {name}:{version}"


@pytest.mark.parametrize(("name", "version"), ALL_TEMPLATES)
async def test_all_prompts_render(service: PromptService, name: str, version: str) -> None:
    template = service.get_template(name, version)

    variables = {variable: f"<{variable}>" for variable in template.variables}

    result = await service.render(
        PromptRenderRequest(
            template_name=name,
            version=version,
            variables=variables,
        )
    )

    assert result.rendered_prompt
    assert "{" not in result.rendered_prompt
    assert "}" not in result.rendered_prompt
    assert result.estimated_tokens is not None
    assert result.estimated_tokens > 0
