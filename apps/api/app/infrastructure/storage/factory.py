from app.core.settings import Settings
from app.infrastructure.storage.interfaces import DocumentStorage
from app.infrastructure.storage.s3 import S3StorageService


def create_storage(settings: Settings) -> DocumentStorage:
    """Create the configured storage implementation."""

    return S3StorageService(settings)
