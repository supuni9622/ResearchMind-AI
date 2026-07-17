"""
Shared reader plumbing every concrete artifact reader builds on --
the read-side counterpart to `writers/base.py`.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from app.ai.artifacts.exceptions import ArtifactNotFoundError
from app.infrastructure.storage.interfaces import DocumentStorage

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseArtifactReader:
    """
    Base class for concrete artifact readers. Stores the storage
    provider and exposes `_read_json`/`_read_json_optional` so
    subclasses only implement their own `read()` reassembly.
    """

    def __init__(
        self,
        storage_provider: DocumentStorage,
    ) -> None:
        self._storage = storage_provider

    async def _read_json(
        self,
        *,
        key: str,
        model: type[ModelT],
    ) -> ModelT:
        """
        Downloads and parses a required file. Raises
        `ArtifactNotFoundError` when the key does not exist.
        """

        if not await self._storage.exists(key=key):
            raise ArtifactNotFoundError(f"Required artifact file '{key}' was not found.")

        raw = await self._storage.download(key=key)

        return model.model_validate_json(raw)

    async def _read_json_optional(
        self,
        *,
        key: str,
        model: type[ModelT],
    ) -> ModelT | None:
        """
        Downloads and parses an optional file, returning `None` when the
        key does not exist rather than raising.
        """

        if not await self._storage.exists(key=key):
            return None

        raw = await self._storage.download(key=key)

        return model.model_validate_json(raw)
