from __future__ import annotations

from uuid import uuid4

from app.ai.artifacts.agent.builders import AgentArtifactBuilder
from app.ai.artifacts.agent.readers import AgentArtifactReader
from app.ai.artifacts.agent.writers import AgentArtifactWriter

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


async def test_write_then_read_roundtrips(fake_storage: FakeDocumentStorage) -> None:
    writer = AgentArtifactWriter(storage_provider=fake_storage)
    reader = AgentArtifactReader(storage_provider=fake_storage)

    run_id = uuid4()
    artifact = AgentArtifactBuilder().build(
        run_id=run_id,
        state={"status": "running"},
        tools={"available": ["search"]},
        execution_graph={"nodes": []},
        events={"events": []},
        memory={"facts": []},
    )

    await writer.write(artifact)

    base = f"artifacts/agents/{run_id}"
    assert set(fake_storage.uploads.keys()) == {
        f"{base}/state.json",
        f"{base}/tools.json",
        f"{base}/execution_graph.json",
        f"{base}/events.json",
        f"{base}/memory.json",
    }

    read_back = await reader.read(run_id)
    assert read_back.state == artifact.state
