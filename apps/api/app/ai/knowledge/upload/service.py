# Upload business logic - Upload orchestration

from app.ai.knowledge.upload.interfaces import DocumentStorage
from app.ai.knowledge.upload.models import UploadDocument


class UploadService:
    """Coordinates the document upload workflow."""

    def __init__(
        self,
        storage: DocumentStorage,
    ) -> None:
        self._storage = storage

    async def upload(
        self,
        *,
        document: UploadDocument,
        file,
    ) -> UploadDocument:
        """
        Upload a document to storage.

        Metadata persistence will be added in Step 2.1.7.
        """

        await self._storage.upload(
            key=document.storage_key,
            file=file,
            content_type=document.content_type,
        )

        return document
