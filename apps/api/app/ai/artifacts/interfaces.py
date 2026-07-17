from __future__ import annotations

from typing import Any, Protocol, TypeVar
from uuid import UUID

ArtifactT_co = TypeVar("ArtifactT_co", covariant=True)
ArtifactT_contra = TypeVar("ArtifactT_contra", contravariant=True)


class ArtifactBuilderInterface(Protocol[ArtifactT_co]):
    """
    Builds a canonical artifact from runtime state. Pure -- no knowledge
    of storage or serialization (see `guardrails/artifacts/builders.py`
    for the pattern every concrete builder follows).
    """

    def build(self, **kwargs: Any) -> ArtifactT_co: ...


class ArtifactWriterInterface(Protocol[ArtifactT_contra]):
    """
    Persists a canonical artifact via the application's storage
    abstraction. Raises on failure -- callers are responsible for
    downgrading a write failure to a log line rather than failing the
    run that produced the artifact (see `guardrails/service.py::
    _persist_artifact`).
    """

    async def write(self, artifact: ArtifactT_contra) -> None: ...


class ArtifactReaderInterface(Protocol[ArtifactT_co]):
    """
    Reconstructs a canonical artifact previously persisted by a matching
    `ArtifactWriterInterface`. Raises `ArtifactNotFoundError` when a
    required file is missing.
    """

    async def read(self, artifact_id: UUID) -> ArtifactT_co: ...
