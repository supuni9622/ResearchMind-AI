"""
Application dependency providers.
"""

from app.dependencies.upload import (
    get_document_repository,
    get_document_storage,
    get_file_hasher,
    get_upload_service,
)

__all__ = [
    "get_document_repository",
    "get_document_storage",
    "get_file_hasher",
    "get_upload_service",
]
