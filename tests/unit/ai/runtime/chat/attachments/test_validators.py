"""
Unit tests for ChatAttachmentValidator.

Mirrors tests/unit/ai/knowledge/upload/test_validators.py (the document
upload validator) -- same shape, image-only constants.
"""

from __future__ import annotations

import pytest
from app.ai.runtime.chat.attachments.constants import (
    MAX_ATTACHMENT_SIZE_BYTES,
    SUPPORTED_IMAGE_CONTENT_TYPES,
    SUPPORTED_IMAGE_EXTENSIONS,
)
from app.ai.runtime.chat.attachments.exceptions import (
    AttachmentTooLargeError,
    EmptyAttachmentError,
    InvalidAttachmentFilenameError,
    UnsupportedAttachmentContentTypeError,
    UnsupportedAttachmentExtensionError,
)
from app.ai.runtime.chat.attachments.validators import ChatAttachmentValidator

_VALID_KWARGS = {
    "filename": "photo.png",
    "content_type": "image/png",
    "size_bytes": 1024,
}


def _validate(**overrides: object) -> None:
    kwargs = {**_VALID_KWARGS, **overrides}
    ChatAttachmentValidator.validate(**kwargs)  # type: ignore[arg-type]


class TestInvalidFilename:
    def test_empty_filename_raises(self) -> None:
        with pytest.raises(InvalidAttachmentFilenameError):
            _validate(filename="")

    def test_whitespace_only_filename_raises(self) -> None:
        with pytest.raises(InvalidAttachmentFilenameError):
            _validate(filename="   ")


class TestUnsupportedExtension:
    def test_unknown_extension_raises(self) -> None:
        with pytest.raises(UnsupportedAttachmentExtensionError):
            _validate(filename="malware.exe")

    def test_no_extension_raises(self) -> None:
        with pytest.raises(UnsupportedAttachmentExtensionError):
            _validate(filename="README")

    def test_document_extension_raises(self) -> None:
        """A knowledge-base document type must not slip through the
        chat-attachment (image-only) validator."""
        with pytest.raises(UnsupportedAttachmentExtensionError):
            _validate(filename="report.pdf", content_type="application/pdf")

    @pytest.mark.parametrize("extension", sorted(SUPPORTED_IMAGE_EXTENSIONS))
    def test_uppercase_extension_is_normalized(self, extension: str) -> None:
        content_type = _content_type_for_extension(extension)
        _validate(
            filename=f"photo{extension.upper()}",
            content_type=content_type,
        )


def _content_type_for_extension(extension: str) -> str:
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    return mapping[extension]


class TestUnsupportedContentType:
    def test_unknown_content_type_raises(self) -> None:
        with pytest.raises(UnsupportedAttachmentContentTypeError):
            _validate(content_type="application/octet-stream")

    def test_spoofed_extension_with_mismatched_mime_raises(self) -> None:
        with pytest.raises(UnsupportedAttachmentContentTypeError):
            _validate(filename="fake.png", content_type="application/pdf")


class TestEmptyAttachment:
    def test_zero_size_raises(self) -> None:
        with pytest.raises(EmptyAttachmentError):
            _validate(size_bytes=0)

    def test_negative_size_raises(self) -> None:
        with pytest.raises(EmptyAttachmentError):
            _validate(size_bytes=-1)


class TestAttachmentSizeBoundary:
    def test_exact_max_size_is_accepted(self) -> None:
        _validate(size_bytes=MAX_ATTACHMENT_SIZE_BYTES)

    def test_one_byte_over_max_raises(self) -> None:
        with pytest.raises(AttachmentTooLargeError):
            _validate(size_bytes=MAX_ATTACHMENT_SIZE_BYTES + 1)


class TestSupportedFilesPass:
    @pytest.mark.parametrize(
        ("filename", "content_type"),
        [
            ("photo.png", "image/png"),
            ("photo.jpg", "image/jpeg"),
            ("photo.jpeg", "image/jpeg"),
            ("photo.webp", "image/webp"),
            ("photo.gif", "image/gif"),
        ],
    )
    def test_supported_pair_does_not_raise(
        self,
        filename: str,
        content_type: str,
    ) -> None:
        assert content_type in SUPPORTED_IMAGE_CONTENT_TYPES
        _validate(filename=filename, content_type=content_type, size_bytes=10)
