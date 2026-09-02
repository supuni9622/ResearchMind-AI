from __future__ import annotations

import time
import uuid
from typing import BinaryIO

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.runtime.chat.attachments.validators import ChatAttachmentValidator
from app.ai.runtime.generation.models import GenerationAttachment
from app.exceptions.base import NotFoundException
from app.infrastructure.storage.interfaces import DocumentStorage
from app.infrastructure.storage.key_generator import StorageKeyGenerator
from app.models.chat_attachment import ChatAttachment
from app.repositories.chat_attachment import ChatAttachmentRepository

logger = structlog.get_logger()

# Presigned URLs handed to a provider need to outlive the generation call
# (routing + the provider fetching the image itself), but are otherwise
# only ever used once -- short-lived on purpose.
ATTACHMENT_URL_TTL_SECONDS = 15 * 60


class ChatAttachmentService:
    """
    Coordinates the chat-attachment upload workflow.

    Deliberately simpler than `UploadService`: no dedup hashing, no
    processing-queue enqueue -- these images aren't RAG-indexed, just
    stored and referenced by a presigned URL when building a
    `GenerationRequest`.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        storage: DocumentStorage,
        repository: ChatAttachmentRepository,
    ) -> None:
        self._session = session
        self._storage = storage
        self._repository = repository

    async def upload(
        self,
        *,
        owner_id: uuid.UUID,
        filename: str,
        content_type: str,
        size_bytes: int,
        file: BinaryIO,
    ) -> ChatAttachment:
        """
        Upload a chat image attachment to S3 and persist its metadata.
        """

        ChatAttachmentValidator.validate(
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
        )

        start = time.perf_counter()

        attachment_id = uuid.uuid4()

        storage_key = StorageKeyGenerator.generate_chat_attachment_key(
            owner_id=owner_id,
            attachment_id=attachment_id,
            filename=filename,
        )

        uploaded_to_storage = False

        try:
            await self._storage.upload(
                key=storage_key,
                file=file,
                content_type=content_type,
            )

            uploaded_to_storage = True

            attachment = ChatAttachment(
                id=attachment_id,
                owner_id=owner_id,
                filename=filename,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size_bytes,
            )

            await self._repository.create(attachment)

            await self._session.commit()

            await self._session.refresh(attachment)

            duration_ms = round((time.perf_counter() - start) * 1000, 2)

            logger.info(
                "chat_attachment.uploaded",
                attachment_id=str(attachment.id),
                owner_id=str(owner_id),
                filename=filename,
                storage_key=storage_key,
                content_type=content_type,
                size_bytes=size_bytes,
                duration_ms=duration_ms,
            )

            return attachment

        except Exception as exc:
            logger.exception(
                "chat_attachment.upload_failed",
                owner_id=str(owner_id),
                filename=filename,
                exc_type=type(exc).__name__,
            )

            await self._session.rollback()

            if uploaded_to_storage:
                try:
                    await self._storage.delete(key=storage_key)
                    logger.info(
                        "chat_attachment.storage_cleanup_succeeded",
                        storage_key=storage_key,
                    )
                except Exception:
                    logger.warning(
                        "chat_attachment.storage_cleanup_failed",
                        storage_key=storage_key,
                    )

            raise

    async def generate_view_url(
        self,
        attachment: ChatAttachment,
    ) -> str:
        """Fresh, short-lived presigned URL for viewing/handing to a
        vision-capable provider."""

        return await self._storage.generate_presigned_url(
            key=attachment.storage_key,
            expires_in=ATTACHMENT_URL_TTL_SECONDS,
        )

    async def resolve_for_generation(
        self,
        attachment_ids: list[uuid.UUID],
        *,
        owner_id: uuid.UUID,
    ) -> list[GenerationAttachment]:
        """
        Resolve owned attachment ids into `GenerationAttachment`s (a fresh
        presigned URL each) for building a `GenerationRequest`.

        Raises `NotFoundException` if any id doesn't resolve to an
        attachment owned by `owner_id` -- deliberately generic (no
        distinction between "doesn't exist" and "belongs to someone
        else") so this can't be used to probe for other users' ids.
        """

        if not attachment_ids:
            return []

        attachments = await self._repository.get_by_ids_for_owner(
            attachment_ids,
            owner_id=owner_id,
        )

        if len(attachments) != len(set(attachment_ids)):
            raise NotFoundException("One or more attachments were not found.")

        by_id = {attachment.id: attachment for attachment in attachments}

        return [
            GenerationAttachment(
                url=await self.generate_view_url(by_id[attachment_id]),
                content_type=by_id[attachment_id].content_type,
            )
            for attachment_id in attachment_ids
        ]
