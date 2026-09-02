"""
Unit tests for ChatAttachmentService.

Mirrors tests/unit/ai/knowledge/upload/test_service.py (the document
upload service) for the upload path, plus `resolve_for_generation` --
the owner-scoped lookup + presigned-URL step `chat.py._resolve_attachments`
uses to build a `GenerationRequest`.
"""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock

import pytest
from app.ai.runtime.chat.attachments.constants import MAX_ATTACHMENT_SIZE_BYTES
from app.ai.runtime.chat.attachments.exceptions import (
    ChatAttachmentValidationError,
    UnsupportedAttachmentExtensionError,
)
from app.ai.runtime.chat.attachments.service import ChatAttachmentService
from app.exceptions.base import NotFoundException
from app.models.chat_attachment import ChatAttachment

_OWNER_ID = uuid.uuid4()


def _make_deps() -> dict[str, AsyncMock]:
    session = AsyncMock()
    storage = AsyncMock()
    repository = AsyncMock()

    storage.upload = AsyncMock(return_value=None)
    storage.delete = AsyncMock(return_value=None)
    storage.generate_presigned_url = AsyncMock(return_value="https://s3.example/signed")

    async def _create(attachment: ChatAttachment) -> ChatAttachment:
        return attachment

    repository.create = AsyncMock(side_effect=_create)

    return {"session": session, "storage": storage, "repository": repository}


def _make_service(deps: dict[str, AsyncMock]) -> ChatAttachmentService:
    return ChatAttachmentService(
        session=deps["session"],
        storage=deps["storage"],
        repository=deps["repository"],
    )


def _upload_kwargs(**overrides: object) -> dict:
    kwargs = {
        "owner_id": _OWNER_ID,
        "filename": "photo.png",
        "content_type": "image/png",
        "size_bytes": 1024,
        "file": io.BytesIO(b"\x89PNG fake image bytes"),
    }
    kwargs.update(overrides)
    return kwargs


class TestInvalidAttachmentsRejectedBeforeIO:
    async def test_unsupported_extension_raises_and_touches_nothing(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(ChatAttachmentValidationError):
            await service.upload(**_upload_kwargs(filename="malware.exe"))

        deps["storage"].upload.assert_not_called()
        deps["repository"].create.assert_not_called()

    async def test_document_content_type_raises(self) -> None:
        """Wave 4 chat attachments are images only -- a document upload
        must not be reachable through this path."""
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(UnsupportedAttachmentExtensionError):
            await service.upload(
                **_upload_kwargs(filename="report.pdf", content_type="application/pdf"),
            )

        deps["storage"].upload.assert_not_called()


class TestAttachmentSizeBoundary:
    async def test_file_over_max_size_rejected_before_upload(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        with pytest.raises(ChatAttachmentValidationError):
            await service.upload(
                **_upload_kwargs(size_bytes=MAX_ATTACHMENT_SIZE_BYTES + 1),
            )

        deps["storage"].upload.assert_not_called()

    async def test_file_at_max_size_is_accepted(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        attachment = await service.upload(
            **_upload_kwargs(size_bytes=MAX_ATTACHMENT_SIZE_BYTES),
        )

        assert attachment.size_bytes == MAX_ATTACHMENT_SIZE_BYTES
        deps["storage"].upload.assert_awaited_once()


class TestStorageFailureCleanup:
    async def test_db_persist_failure_after_successful_upload_cleans_up_storage(
        self,
    ) -> None:
        deps = _make_deps()
        deps["repository"].create = AsyncMock(side_effect=RuntimeError("db unavailable"))
        service = _make_service(deps)

        with pytest.raises(RuntimeError, match="db unavailable"):
            await service.upload(**_upload_kwargs())

        deps["storage"].upload.assert_awaited_once()
        deps["storage"].delete.assert_awaited_once()
        deps["session"].rollback.assert_awaited_once()

    async def test_cleanup_failure_does_not_mask_original_error(self) -> None:
        deps = _make_deps()
        deps["repository"].create = AsyncMock(side_effect=RuntimeError("db unavailable"))
        deps["storage"].delete = AsyncMock(side_effect=RuntimeError("delete also failed"))
        service = _make_service(deps)

        with pytest.raises(RuntimeError, match="db unavailable"):
            await service.upload(**_upload_kwargs())

        deps["storage"].delete.assert_awaited_once()


class TestResolveForGeneration:
    async def test_empty_ids_short_circuits_with_no_lookup(self) -> None:
        deps = _make_deps()
        service = _make_service(deps)

        result = await service.resolve_for_generation([], owner_id=_OWNER_ID)

        assert result == []
        deps["repository"].get_by_ids_for_owner.assert_not_called()

    async def test_resolves_owned_attachments_with_fresh_urls(self) -> None:
        deps = _make_deps()
        attachment_id = uuid.uuid4()
        attachment = ChatAttachment(
            id=attachment_id,
            owner_id=_OWNER_ID,
            filename="photo.png",
            storage_key="chat-attachments/owner/attachment/original.png",
            content_type="image/png",
            size_bytes=1024,
        )
        deps["repository"].get_by_ids_for_owner = AsyncMock(return_value=[attachment])
        service = _make_service(deps)

        result = await service.resolve_for_generation([attachment_id], owner_id=_OWNER_ID)

        assert len(result) == 1
        assert result[0].url == "https://s3.example/signed"
        assert result[0].content_type == "image/png"

    async def test_missing_or_foreign_id_raises_not_found(self) -> None:
        """An id that doesn't resolve (wrong owner, or doesn't exist) must
        raise generically -- not distinguish the two, so this can't be
        used to probe for other users' attachment ids."""
        deps = _make_deps()
        deps["repository"].get_by_ids_for_owner = AsyncMock(return_value=[])
        service = _make_service(deps)

        with pytest.raises(NotFoundException):
            await service.resolve_for_generation([uuid.uuid4()], owner_id=_OWNER_ID)
