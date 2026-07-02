"""
Duplicate detection service.

Determines whether a document already exists for a user based on its
SHA256 checksum.

Hash computation is intentionally outside this service and delegated to
the application's FileHasher implementation.
"""

from __future__ import annotations

from uuid import UUID

from app.ai.knowledge.upload.duplicate.models import (
    DuplicateCheckResult,
)
from app.repositories.document import DocumentRepository


class DuplicateDetectionService:
    """
    Performs exact duplicate detection using SHA256 checksums.
    """

    def __init__(
        self,
        repository: DocumentRepository,
    ) -> None:
        self._repository = repository

    async def check(
        self,
        *,
        owner_id: UUID,
        sha256: str,
    ) -> DuplicateCheckResult:
        """
        Determine whether a document with the supplied checksum already
        exists for the owner.
        """

        document = await self._repository.find_by_owner_and_hash(
            owner_id=owner_id,
            sha256=sha256,
        )

        if document is None:
            return DuplicateCheckResult(
                is_duplicate=False,
            )

        return DuplicateCheckResult(
            is_duplicate=True,
            document=document,
        )
