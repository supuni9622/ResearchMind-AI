"""
SHA256 duplicate detection provider.
"""

from __future__ import annotations

import hashlib
from typing import BinaryIO

from app.ai.knowledge.upload.duplicate.exceptions import (
    DuplicateHashingError,
)


class SHA256DuplicateProvider:
    """
    Computes SHA256 hashes for uploaded documents.
    """

    chunk_size = 1024 * 1024

    async def compute_hash(
        self,
        file: BinaryIO,
    ) -> str:
        """
        Compute a SHA256 hash for a file stream.

        The file position is restored before returning.
        """

        try:
            file.seek(0)

            digest = hashlib.sha256()

            while chunk := file.read(self.chunk_size):
                digest.update(chunk)

            file.seek(0)

            return digest.hexdigest()

        except Exception as exc:
            raise DuplicateHashingError("Failed to compute SHA256 hash.") from exc
