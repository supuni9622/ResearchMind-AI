"""
Dependency providers for the document upload workflow.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge.upload.service import UploadService
from app.core.settings import settings
from app.db.session import get_db
from app.infrastructure.hashing import FileHasher, SHA256Hasher
from app.infrastructure.storage import DocumentStorage, create_storage
from app.repositories.document import DocumentRepository


def _get_storage() -> DocumentStorage:
    """
    Create the configured document storage service.

    The instance is cached because it is stateless and
    safe to reuse across requests.
    """

    return create_storage(settings)


@lru_cache
def _get_hasher() -> FileHasher:
    """
    Create the configured file hasher.

    The hasher is stateless and safe to reuse.
    """

    return SHA256Hasher()


def get_document_repository(
    session: AsyncSession = Depends(get_db),
) -> DocumentRepository:
    """
    Create a DocumentRepository.
    """

    return DocumentRepository(session)


def get_document_storage() -> DocumentStorage:
    """
    Return the configured document storage service.
    """

    return _get_storage()


def get_file_hasher() -> FileHasher:
    """
    Return the configured file hasher.
    """

    return _get_hasher()


def get_upload_service(
    session: AsyncSession = Depends(get_db),
    repository: DocumentRepository = Depends(
        get_document_repository,
    ),
    storage: DocumentStorage = Depends(
        get_document_storage,
    ),
    hasher: FileHasher = Depends(
        get_file_hasher,
    ),
) -> UploadService:
    """
    Create the UploadService.
    """

    return UploadService(
        session=session,
        repository=repository,
        storage=storage,
        hasher=hasher,
    )
