from __future__ import annotations

from app.ai.artifacts.writers.base import BaseArtifactWriter, write_json_artifact
from pydantic import BaseModel

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


class _Payload(BaseModel):
    name: str
    optional_field: str | None = None


async def test_write_json_artifact_uploads_serialized_json(
    fake_storage: FakeDocumentStorage,
) -> None:
    await write_json_artifact(
        fake_storage,
        key="some/key.json",
        payload=_Payload(name="hello"),
    )

    assert fake_storage.uploads["some/key.json"] == b'{\n  "name": "hello"\n}'


async def test_write_json_artifact_excludes_none_fields(
    fake_storage: FakeDocumentStorage,
) -> None:
    await write_json_artifact(
        fake_storage,
        key="some/key.json",
        payload=_Payload(name="hello", optional_field=None),
    )

    assert b"optional_field" not in fake_storage.uploads["some/key.json"]


async def test_base_artifact_writer_write_json_delegates(
    fake_storage: FakeDocumentStorage,
) -> None:
    class _ConcreteWriter(BaseArtifactWriter):
        async def write(self, artifact: _Payload) -> None:
            await self._write_json(key="concrete/key.json", payload=artifact)

    writer = _ConcreteWriter(fake_storage)

    await writer.write(_Payload(name="world"))

    assert fake_storage.uploads["concrete/key.json"] == b'{\n  "name": "world"\n}'
