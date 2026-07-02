from __future__ import annotations

import structlog
from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    status,
)

from app.ai.knowledge.processing.enums import DocumentFormat
from app.ai.knowledge.processing.interfaces import ParseRequest
from app.ai.knowledge.upload.service import UploadService
from app.auth.dependencies import get_current_user
from app.dependencies import (
    get_document_processing_service,
    get_upload_service,
)
from app.exceptions.base import ValidationException
from app.models.user import User
from app.schemas.document import DocumentUploadResponse
from app.services.document_processing_service import (
    DocumentProcessingService,
)

logger = structlog.get_logger()

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
    upload_service: UploadService = Depends(get_upload_service),
    processing_service: DocumentProcessingService = Depends(
        get_document_processing_service,
    ),
) -> DocumentUploadResponse:
    """
    Upload a document to ResearchMind.

    Workflow:

    1. Validate upload
    2. Upload original document to S3
    3. Persist document metadata
    4. Trigger synchronous document processing
    5. Return uploaded document metadata

    Processing failures do not fail the upload request.
    The document processing status records the outcome.
    """

    if not file.filename:
        raise ValidationException(
            message="Uploaded file must have a filename.",
        )

    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)

    document = await upload_service.upload(
        owner_id=current_user.id,
        filename=file.filename,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        file=file.file,
    )

    parse_request = ParseRequest(
        document_id=document.id,
        storage_key=document.storage_key,
        filename=document.filename,
        content_type=document.content_type,
        document_format=DocumentFormat.from_content_type(
            document.content_type,
        ),
    )

    try:
        await processing_service.process(
            document=document,
            request=parse_request,
        )
    except Exception:
        logger.exception(
            "document.processing_failed_after_upload",
            document_id=str(document.id),
            owner_id=str(current_user.id),
        )

    return DocumentUploadResponse.model_validate(document)
