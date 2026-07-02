"""
Unit tests for TemporaryFileManager.

Covers:
- The temp file is created and visible while the context is open
- Written contents match exactly what was passed in
- The original filename's extension is preserved on the temp file
- The temp file is deleted once the context exits
- The temp file is still deleted if an exception is raised inside the
  context (cleanup must not depend on a clean exit)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from app.ai.knowledge.processing.temporary_file_manager import (
    TemporaryFileManager,
)


class TestTemporaryFileCreation:
    async def test_file_is_created(self) -> None:
        manager = TemporaryFileManager()

        async with manager.create(content=b"hello", filename="doc.txt") as path:
            assert path.exists()
            assert path.is_file()

    async def test_contents_are_written_correctly(self) -> None:
        manager = TemporaryFileManager()
        content = b"the quick brown fox jumps over the lazy dog"

        async with manager.create(content=content, filename="doc.txt") as path:
            assert path.read_bytes() == content

    @pytest.mark.parametrize(
        "filename",
        ["report.pdf", "notes.md", "data.txt", "contract.docx"],
    )
    async def test_extension_is_preserved(self, filename: str) -> None:
        manager = TemporaryFileManager()

        async with manager.create(content=b"data", filename=filename) as path:
            assert path.suffix == Path(filename).suffix


class TestTemporaryFileCleanup:
    async def test_file_is_deleted_after_context_exit(self) -> None:
        manager = TemporaryFileManager()

        async with manager.create(content=b"data", filename="doc.txt") as path:
            created_path = path

        assert not created_path.exists()

    async def test_cleanup_happens_even_if_exception_raised_inside_context(
        self,
    ) -> None:
        manager = TemporaryFileManager()
        created_path: Path | None = None

        with pytest.raises(RuntimeError, match="boom"):
            async with manager.create(content=b"data", filename="doc.txt") as path:
                created_path = path
                assert created_path.exists()
                raise RuntimeError("boom")

        assert created_path is not None
        assert not created_path.exists()

    async def test_cleanup_does_not_raise_if_file_already_removed(self) -> None:
        """
        Guards the `suppress(FileNotFoundError)` in the manager: if the
        caller (or another process) already removed the temp file before
        the context exits, cleanup must not raise.
        """
        manager = TemporaryFileManager()

        async with manager.create(content=b"data", filename="doc.txt") as path:
            os.remove(path)
