"""
Temporary file manager.

Provides temporary files for document processing.

Responsibilities:

- Create temporary files from downloaded document bytes
- Preserve the original file extension
- Clean up temporary files after processing

This component isolates filesystem concerns from the parser
implementations and processing pipeline.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path


class TemporaryFileManager:
    """
    Creates temporary files for document processing.
    """

    @asynccontextmanager
    async def create(
        self,
        *,
        content: bytes,
        filename: str,
    ) -> AsyncIterator[Path]:
        """
        Create a temporary file.

        The file is automatically deleted when the context exits.

        Args:
            content:
                File contents.

            filename:
                Original filename. Used only to preserve the extension.

        Yields:
            Path to the temporary file.
        """

        suffix = Path(filename).suffix

        fd, path = tempfile.mkstemp(
            suffix=suffix,
        )

        try:
            with os.fdopen(fd, "wb") as file:
                file.write(content)

            yield Path(path)

        finally:
            with suppress(FileNotFoundError):
                os.remove(path)
