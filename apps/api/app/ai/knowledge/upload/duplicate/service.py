"""
Duplicate detection service.
"""

from __future__ import annotations

from typing import BinaryIO
from uuid import UUID

from app.ai.knowledge.upload.duplicate.models import (
    DuplicateCheckRequest,
    DuplicateCheckResult,
)
from app.ai.knowledge.upload.duplicate.providers.sha256 import (
    SHA256DuplicateProvider,
)
from app.repositories.document import DocumentRepository


class DuplicateDetectionService:
    """
    Performs exact duplicate detection using SHA256.
    """

    def __init__(
        self,
        *,
        provider: SHA256DuplicateProvider,
        repository: DocumentRepository,
    ) -> None:
        self._provider = provider
        self._repository = repository

    async def check(
        self,
        *,
        owner_id: UUID,
        file: BinaryIO,
    ) -> DuplicateCheckResult:
        """
        Determine whether the uploaded file already exists.
        """

        sha256 = await self._provider.compute_hash(file)

        request = DuplicateCheckRequest(
            owner_id=owner_id,
            sha256=sha256,
        )

        document = await self._repository.find_by_owner_and_hash(
            owner_id=request.owner_id,
            sha256=request.sha256,
        )

        if document is None:
            return DuplicateCheckResult(
                is_duplicate=False,
            )

        return DuplicateCheckResult(
            is_duplicate=True,
            existing_document_id=document.id,
        )
