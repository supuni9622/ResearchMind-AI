# Storage implementations - S3 storage implementation
from app.ai.knowledge.upload.interfaces import DocumentStorage


class S3StorageService(DocumentStorage):
    """Amazon S3 document storage."""

    async def upload(self, *, key, file, content_type):
        raise NotImplementedError

    async def download(self, *, key):
        raise NotImplementedError

    async def delete(self, *, key):
        raise NotImplementedError

    async def exists(self, *, key):
        raise NotImplementedError

    async def generate_presigned_url(
        self,
        *,
        key,
        expires_in=3600,
    ):
        raise NotImplementedError
