from __future__ import annotations

import asyncio
import hashlib
from typing import BinaryIO

from app.infrastructure.hashing.exceptions import HashingError
from app.infrastructure.hashing.interfaces import FileHasher


class SHA256Hasher(FileHasher):
    """SHA-256 implementation."""

    CHUNK_SIZE = 1024 * 1024  # 1 MB

    async def hash_file(
        self,
        file: BinaryIO,
    ) -> str:
        return await asyncio.to_thread(
            self._calculate,
            file,
        )

    def _calculate(
        self,
        file: BinaryIO,
    ) -> str:
        try:
            digest = hashlib.sha256()

            file.seek(0)

            while chunk := file.read(self.CHUNK_SIZE):
                digest.update(chunk)

            file.seek(0)

            return digest.hexdigest()

        except Exception as exc:
            raise HashingError(str(exc)) from exc


# Why chunked reading?

# Instead of:
# file.read()
# we use:
# while chunk := file.read(...)

# Benefits:
# Supports very large files
# Constant memory usage
# Production standard
# Reusable for future 500 MB+ uploads
