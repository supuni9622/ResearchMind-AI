from __future__ import annotations

import asyncio
import hashlib
import time
from typing import BinaryIO

import structlog
from app.infrastructure.hashing.exceptions import HashingError
from app.infrastructure.hashing.interfaces import FileHasher

logger = structlog.get_logger()


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
        start = time.perf_counter()
        try:
            digest = hashlib.sha256()

            file.seek(0)
            bytes_read = 0

            while chunk := file.read(self.CHUNK_SIZE):
                digest.update(chunk)
                bytes_read += len(chunk)

            file.seek(0)

            hexdigest = digest.hexdigest()

            logger.debug(
                "hasher.sha256_complete",
                bytes_read=bytes_read,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
            )

            return hexdigest

        except Exception as exc:
            logger.warning("hasher.sha256_failed", reason=str(exc))
            raise HashingError(str(exc)) from exc
