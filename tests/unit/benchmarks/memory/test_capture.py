from __future__ import annotations

import json

import httpx
import pytest

from benchmarks.memory.capture import MemoryCaptureConfig, capture_live_memory_results
from benchmarks.memory.dataset import MemoryEvaluationDataset, MemoryEvaluationQuery


@pytest.mark.asyncio
async def test_capture_calls_real_api_contract_and_maps_ids() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/search"):
            assert json.loads(request.content)["scope_type"] == "project"
            return httpx.Response(
                200,
                json={
                    "memories": [{"id": "real-a"}, {"id": "real-unknown"}],
                    "latency_ms": 1,
                },
            )
        return httpx.Response(
            200,
            json={
                "session_memories": [],
                "user_memories": [{"id": "real-personal"}],
                "semantic_memories": [{"id": "real-a"}],
                "research_memories": [],
            },
        )

    dataset = MemoryEvaluationDataset(
        name="test",
        version="1",
        queries=[
            MemoryEvaluationQuery(
                query_id="q",
                query="query",
                category="project_isolation",
                scope_type="project",
                project_key="project-a",
                session_key="project-a",
                relevant_memory_ids=["a"],
                allowed_memory_ids=["a", "personal"],
            )
        ],
    )
    config = MemoryCaptureConfig(
        candidate="staging",
        version="sha",
        credentials={"default": "token"},
        projects={"project-a": "project-uuid"},
        sessions={"project-a": "session-uuid"},
        memory_ids={"a": "real-a", "personal": "real-personal"},
    )
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="https://example.test"
    ) as client:
        captured = await capture_live_memory_results(
            dataset=dataset,
            config=config,
            base_url="https://example.test",
            client=client,
        )

    assert captured.results[0].retrieved_memory_ids == [
        "a",
        "unmapped:real-unknown",
    ]
    assert captured.results[0].selected_memory_ids == ["personal", "a"]
    assert requests[0].headers["authorization"] == "Bearer token"
    assert requests[1].url.params["project_id"] == "project-uuid"


@pytest.mark.asyncio
async def test_capture_rejects_incomplete_external_mapping() -> None:
    dataset = MemoryEvaluationDataset(
        name="test",
        version="1",
        queries=[
            MemoryEvaluationQuery(
                query_id="q",
                query="query",
                category="exact_recall",
                relevant_memory_ids=[],
                allowed_memory_ids=[],
            )
        ],
    )
    config = MemoryCaptureConfig(
        candidate="staging",
        version="sha",
        credentials={},
        projects={},
        sessions={},
        memory_ids={},
    )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda _: httpx.Response(500))
    ) as client:
        with pytest.raises(ValueError, match="incomplete"):
            await capture_live_memory_results(
                dataset=dataset,
                config=config,
                base_url="https://example.test",
                client=client,
            )
