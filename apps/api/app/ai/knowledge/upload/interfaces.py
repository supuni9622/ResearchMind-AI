# Storage abstractions - Storage contracts (S3, Local, etc.)
from abc import ABC, abstractmethod
from typing import BinaryIO


class DocumentStorage(ABC):
    """Abstract interface for document storage providers."""

    @abstractmethod
    async def upload(
        self,
        *,
        key: str,
        file: BinaryIO,
        content_type: str,
    ) -> None:
        """Upload a document."""

    @abstractmethod
    async def download(
        self,
        *,
        key: str,
    ) -> bytes:
        """Download a document."""

    @abstractmethod
    async def delete(
        self,
        *,
        key: str,
    ) -> None:
        """Delete a document."""

    @abstractmethod
    async def exists(
        self,
        *,
        key: str,
    ) -> bool:
        """Return whether a document exists."""

    @abstractmethod
    async def generate_presigned_url(
        self,
        *,
        key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate a temporary download URL."""
