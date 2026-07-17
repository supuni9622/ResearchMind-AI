from __future__ import annotations

from typing import BinaryIO

import pytest
from app.infrastructure.storage.interfaces import DocumentStorage


class FakeDocumentStorage(DocumentStorage):
    """
    In-memory `DocumentStorage` double shared across Artifact Platform
    tests -- same shape as `tests/unit/ai/guardrails/artifacts/
    test_writers.py::_FakeDocumentStorage`.
    """

    def __init__(self) -> None:
        self.uploads: dict[str, bytes] = {}

    async def upload(self, *, key: str, file: BinaryIO, content_type: str) -> None:
        self.uploads[key] = file.read()

    async def download(self, *, key: str) -> bytes:
        return self.uploads[key]

    async def delete(self, *, key: str) -> None:
        del self.uploads[key]

    async def exists(self, *, key: str) -> bool:
        return key in self.uploads

    async def generate_presigned_url(self, *, key: str, expires_in: int = 3600) -> str:
        return f"https://example.test/{key}"

    async def list_keys(self, *, prefix: str) -> list[str]:
        return [key for key in self.uploads if key.startswith(prefix)]


@pytest.fixture
def fake_storage() -> FakeDocumentStorage:
    return FakeDocumentStorage()
