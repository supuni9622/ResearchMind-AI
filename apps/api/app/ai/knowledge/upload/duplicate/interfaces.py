"""
Interfaces for duplicate document detection.

The upload workflow depends only on these abstractions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO

from app.ai.knowledge.upload.duplicate.models import (
    DuplicateCheckRequest,
    DuplicateCheckResult,
)


class DuplicateDetector(ABC):
    """
    Contract implemented by duplicate detection strategies.
    """

    @property
    @abstractmethod
    def detector_name(self) -> str:
        """
        Human-readable detector name.
        """

    @abstractmethod
    async def compute_hash(
        self,
        file: BinaryIO,
    ) -> str:
        """
        Compute the content hash for a document.

        Implementations must rewind the stream before returning.
        """

    @abstractmethod
    async def check(
        self,
        request: DuplicateCheckRequest,
    ) -> DuplicateCheckResult:
        """
        Determine whether the supplied document is a duplicate.
        """
