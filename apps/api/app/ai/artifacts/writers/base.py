"""
Shared writer plumbing every concrete artifact writer builds on.

Extracted from `guardrails/artifacts/writers.py::GuardrailArtifactWriter`
so the same `BytesIO(payload.model_dump_json(...))` upload boilerplate
isn't re-declared per runtime (generation/streaming/conversation/...).
"""

from __future__ import annotations

from io import BytesIO

from pydantic import BaseModel

from app.infrastructure.storage.interfaces import DocumentStorage


async def write_json_artifact(
    storage: DocumentStorage,
    *,
    key: str,
    payload: BaseModel,
) -> None:
    """
    Serializes `payload` to indented, `None`-stripped JSON and uploads it
    to `key`. Never overwrites an existing key on its own -- callers pick
    keys that are unique per write (see the Artifact Platform's
    immutability principle, PRD §5).
    """

    await storage.upload(
        key=key,
        file=BytesIO(
            payload.model_dump_json(
                indent=2,
                exclude_none=True,
            ).encode("utf-8")
        ),
        content_type="application/json",
    )


class BaseArtifactWriter:
    """
    Base class for concrete artifact writers. Stores the storage
    provider and exposes `_write_json` as a bound convenience so
    subclasses only implement their own `write()` orchestration.
    """

    def __init__(
        self,
        storage_provider: DocumentStorage,
    ) -> None:
        self._storage = storage_provider

    async def _write_json(
        self,
        *,
        key: str,
        payload: BaseModel,
    ) -> None:
        await write_json_artifact(
            self._storage,
            key=key,
            payload=payload,
        )
