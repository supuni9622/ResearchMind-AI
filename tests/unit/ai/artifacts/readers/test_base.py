from __future__ import annotations

import pytest
from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.ai.artifacts.readers.base import BaseArtifactReader
from app.ai.artifacts.writers.base import write_json_artifact
from pydantic import BaseModel

from tests.unit.ai.artifacts.conftest import FakeDocumentStorage


class _Payload(BaseModel):
    name: str


async def test_read_json_returns_parsed_model(fake_storage: FakeDocumentStorage) -> None:
    await write_json_artifact(fake_storage, key="some/key.json", payload=_Payload(name="hi"))

    reader = BaseArtifactReader(fake_storage)

    result = await reader._read_json(key="some/key.json", model=_Payload)

    assert result == _Payload(name="hi")


async def test_read_json_raises_not_found_when_missing(
    fake_storage: FakeDocumentStorage,
) -> None:
    reader = BaseArtifactReader(fake_storage)

    with pytest.raises(ArtifactNotFoundError):
        await reader._read_json(key="missing.json", model=_Payload)


async def test_read_json_optional_returns_none_when_missing(
    fake_storage: FakeDocumentStorage,
) -> None:
    reader = BaseArtifactReader(fake_storage)

    result = await reader._read_json_optional(key="missing.json", model=_Payload)

    assert result is None
