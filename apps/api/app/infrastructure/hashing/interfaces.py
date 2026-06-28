from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class FileHasher(ABC):
    """Abstract interface for file hashing."""

    @abstractmethod
    async def hash_file(
        self,
        file: BinaryIO,
    ) -> str:
        """
        Calculate a hexadecimal hash for a file.
        """
