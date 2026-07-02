"""
Unit tests for UploadValidator.

Covers:
- Invalid files: empty/blank filename, unsupported extension,
  unsupported content type, empty (zero-byte) file, negative size
- Large files: exact boundary at MAX_UPLOAD_SIZE_BYTES, one byte over
- Happy path for every supported extension / content-type pair
"""

from __future__ import annotations

import pytest
from app.ai.knowledge.upload.constants import (
    MAX_UPLOAD_SIZE_BYTES,
    SUPPORTED_CONTENT_TYPES,
    SUPPORTED_EXTENSIONS,
)
from app.ai.knowledge.upload.exceptions import (
    EmptyFileError,
    FileTooLargeError,
    InvalidFilenameError,
    UnsupportedContentTypeError,
    UnsupportedExtensionError,
)
from app.ai.knowledge.upload.validators import UploadValidator

_VALID_KWARGS = {
    "filename": "report.pdf",
    "content_type": "application/pdf",
    "size_bytes": 1024,
}


def _validate(**overrides: object) -> None:
    kwargs = {**_VALID_KWARGS, **overrides}
    UploadValidator.validate(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Invalid files
# ---------------------------------------------------------------------------


class TestInvalidFilename:
    def test_empty_filename_raises(self) -> None:
        with pytest.raises(InvalidFilenameError):
            _validate(filename="")

    def test_whitespace_only_filename_raises(self) -> None:
        with pytest.raises(InvalidFilenameError):
            _validate(filename="   ")


class TestUnsupportedExtension:
    def test_unknown_extension_raises(self) -> None:
        with pytest.raises(UnsupportedExtensionError):
            _validate(filename="malware.exe")

    def test_no_extension_raises(self) -> None:
        with pytest.raises(UnsupportedExtensionError):
            _validate(filename="README")

    def test_double_extension_uses_final_suffix(self) -> None:
        """`archive.tar.gz` should be judged on `.gz`, not `.tar`."""
        with pytest.raises(UnsupportedExtensionError):
            _validate(filename="archive.tar.gz")

    @pytest.mark.parametrize("extension", sorted(SUPPORTED_EXTENSIONS))
    def test_uppercase_extension_is_normalized(self, extension: str) -> None:
        """Extension matching is case-insensitive."""
        content_type = next(
            ct for ct in SUPPORTED_CONTENT_TYPES if _extension_matches(ct, extension)
        )
        _validate(
            filename=f"document{extension.upper()}",
            content_type=content_type,
        )


def _extension_matches(content_type: str, extension: str) -> bool:
    mapping = {
        "application/pdf": ".pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
        "text/markdown": ".md",
        "text/plain": ".txt",
    }
    return mapping[content_type] == extension


class TestUnsupportedContentType:
    def test_unknown_content_type_raises(self) -> None:
        with pytest.raises(UnsupportedContentTypeError):
            _validate(content_type="application/octet-stream")

    def test_spoofed_extension_with_mismatched_mime_raises(self) -> None:
        """A `.pdf` filename with an image MIME type must still be rejected."""
        with pytest.raises(UnsupportedContentTypeError):
            _validate(filename="fake.pdf", content_type="image/png")


class TestEmptyFile:
    def test_zero_size_raises(self) -> None:
        with pytest.raises(EmptyFileError):
            _validate(size_bytes=0)

    def test_negative_size_raises(self) -> None:
        with pytest.raises(EmptyFileError):
            _validate(size_bytes=-1)


# ---------------------------------------------------------------------------
# Large files
# ---------------------------------------------------------------------------


class TestFileSizeBoundary:
    def test_exact_max_size_is_accepted(self) -> None:
        _validate(size_bytes=MAX_UPLOAD_SIZE_BYTES)

    def test_one_byte_over_max_raises(self) -> None:
        with pytest.raises(FileTooLargeError):
            _validate(size_bytes=MAX_UPLOAD_SIZE_BYTES + 1)

    def test_far_over_max_raises(self) -> None:
        with pytest.raises(FileTooLargeError):
            _validate(size_bytes=MAX_UPLOAD_SIZE_BYTES * 10)


# ---------------------------------------------------------------------------
# Happy path: every supported extension / content-type pair
# ---------------------------------------------------------------------------


class TestSupportedFilesPass:
    @pytest.mark.parametrize(
        ("filename", "content_type"),
        [
            ("report.pdf", "application/pdf"),
            (
                "report.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("notes.md", "text/markdown"),
            ("notes.txt", "text/plain"),
        ],
    )
    def test_supported_pair_does_not_raise(
        self,
        filename: str,
        content_type: str,
    ) -> None:
        _validate(filename=filename, content_type=content_type, size_bytes=10)
