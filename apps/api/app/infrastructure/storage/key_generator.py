from __future__ import annotations

from pathlib import Path
from uuid import UUID


class StorageKeyGenerator:
    """Generates deterministic S3 object keys."""

    @staticmethod
    def generate_document_key(
        *,
        owner_id: UUID,
        document_id: UUID,
        filename: str,
    ) -> str:
        """
        Generate the storage key for an uploaded document.

        Example:
            documents/{owner_id}/{document_id}/original.pdf
        """

        extension = Path(filename).suffix.lower()

        return f"documents/{owner_id}/{document_id}/original{extension}"
