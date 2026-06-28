from __future__ import annotations

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    status,
)

from app.ai.knowledge.upload.service import UploadService
from app.auth.dependencies import get_current_user
from app.dependencies import get_upload_service
from app.exceptions.base import ValidationException
from app.models.user import User
from app.schemas.document import DocumentUploadResponse

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    service: UploadService = Depends(get_upload_service),
) -> DocumentUploadResponse:
    """
    Upload a document to ResearchMind.

    The document is:

    - validated
    - uploaded to Amazon S3
    - persisted in PostgreSQL

    Returns the uploaded document metadata.
    """

    # ----------------------------------------------------------
    # Calculate file size in a framework-independent way.
    # ----------------------------------------------------------

    if not file.filename:
        raise ValidationException(message="Uploaded file must have a filename.")

    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)

    document = await service.upload(
        owner_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        file=file.file,
    )

    return DocumentUploadResponse.model_validate(document)
