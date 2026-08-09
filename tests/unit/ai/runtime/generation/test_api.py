from types import SimpleNamespace

from app.ai.runtime.generation.enums import GenerationProvider
from app.api.v1.generation import providers


async def test_providers_returns_only_registered_providers() -> None:
    generation_service = SimpleNamespace(
        registry=SimpleNamespace(
            providers=[GenerationProvider.GROQ, GenerationProvider.OLLAMA],
        )
    )

    response = await providers(generation_service)  # type: ignore[arg-type]

    assert response.data.providers == [
        GenerationProvider.GROQ,
        GenerationProvider.OLLAMA,
    ]
