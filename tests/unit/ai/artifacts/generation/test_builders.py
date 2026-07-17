from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.generation.builders import GenerationArtifactBuilder

from tests.unit.ai.artifacts.generation.conftest import make_generation_result


def test_build_maps_core_fields() -> None:
    result = make_generation_result()

    artifact = GenerationArtifactBuilder().build(result=result)

    assert artifact.metadata.generation_id == result.generation_id
    assert artifact.metadata.duration_ms == result.statistics.latency_ms
    assert artifact.metadata.provider == result.provider
    assert artifact.metadata.model == result.model
    assert artifact.response.content == result.content
    assert artifact.routing is None
    assert artifact.cache is None


def test_build_carries_owner_id() -> None:
    owner_id = uuid4()

    artifact = GenerationArtifactBuilder().build(
        result=make_generation_result(),
        owner_id=owner_id,
    )

    assert artifact.metadata.owner_id == owner_id


def test_build_maps_routing_and_cache_metadata_when_present() -> None:
    result = make_generation_result(
        metadata={
            "routing": {
                "strategy": "auto",
                "selected_provider": "groq",
                "selected_model": "llama-3.3-70b",
                "score": 0.9,
                "reasons": ["cheapest"],
                "used_fallback": False,
            },
            "cache": {"hit": True, "level": "l1_exact"},
        },
    )

    artifact = GenerationArtifactBuilder().build(result=result)

    assert artifact.routing is not None
    assert artifact.routing.selected_provider == "groq"
    assert artifact.cache is not None
    assert artifact.cache.hit is True
    assert artifact.cache.level == "l1_exact"
