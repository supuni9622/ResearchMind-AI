from abc import ABC, abstractmethod
from typing import BinaryIO


class DocumentStorage(ABC):
    """Abstract document storage interface."""

    @abstractmethod
    async def upload(
        self,
        *,
        key: str,
        file: BinaryIO,
        content_type: str,
    ) -> None: ...

    @abstractmethod
    async def download(
        self,
        *,
        key: str,
    ) -> bytes: ...

    @abstractmethod
    async def delete(
        self,
        *,
        key: str,
    ) -> None: ...

    @abstractmethod
    async def exists(
        self,
        *,
        key: str,
    ) -> bool: ...

    @abstractmethod
    async def generate_presigned_url(
        self,
        *,
        key: str,
        expires_in: int = 3600,
    ) -> str: ...

    @abstractmethod
    async def list_keys(
        self,
        *,
        prefix: str,
    ) -> list[str]: ...
