from __future__ import annotations

import time
import uuid
from typing import BinaryIO

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.knowledge.upload.validators import UploadValidator
from app.infrastructure.hashing.interfaces import FileHasher
from app.infrastructure.storage.interfaces import DocumentStorage
from app.infrastructure.storage.key_generator import StorageKeyGenerator
from app.models.document import Document
from app.models.enums import DocumentStatus
from app.repositories.document import DocumentRepository

logger = structlog.get_logger()


class UploadService:
    """
    Coordinates the document upload workflow.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: DocumentStorage,
        hasher: FileHasher,
        repository: DocumentRepository,
    ) -> None:
        self._session = session
        self._storage = storage
        self._hasher = hasher
        self._repository = repository

    async def upload(
        self,
        *,
        owner_id: uuid.UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
        file: BinaryIO,
    ) -> Document:
        """
        Upload a document to S3 and persist its metadata.
        """

        UploadValidator.validate(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        start = time.perf_counter()

        storage_key: str | None = None

        try:
            checksum = await self._hasher.hash_file(file)

            # Future enhancement:
            # existing = await self._repository.get_by_checksum(checksum)

            document_id = uuid.uuid4()

            storage_key = StorageKeyGenerator.generate_document_key(
                owner_id=owner_id,
                document_id=document_id,
                filename=filename,
            )

            await self._storage.upload(
                key=storage_key,
                file=file,
                content_type=content_type,
            )

            document = Document(
                id=document_id,
                owner_id=owner_id,
                filename=filename,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size_bytes,
                checksum=checksum,
                status=DocumentStatus.UPLOADED,
            )

            await self._repository.create(document)

            await self._session.commit()

            await self._session.refresh(document)

            duration_ms = round(
                (time.perf_counter() - start) * 1000,
                2,
            )

            logger.info(
                "document.uploaded",
                document_id=str(document.id),
                owner_id=str(owner_id),
                filename=filename,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size_bytes,
                checksum=checksum,
                duration_ms=duration_ms,
            )

            return document

        except Exception:
            logger.exception(
                "document.upload_failed",
                owner_id=str(owner_id),
                filename=filename,
            )

            await self._session.rollback()

            if storage_key is not None:
                try:
                    await self._storage.delete(
                        key=storage_key,
                    )
                except Exception:
                    logger.warning(
                        "upload.storage_cleanup_failed",
                        storage_key=storage_key,
                    )

            raise
