import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.ai.knowledge.retrieval.exceptions import (
    RetrievalError,
    RetrievalExecutionError,
    RetrievalProviderNotFoundError,
    RetrievalValidationError,
)
from app.ai.knowledge.vectorstores.exceptions import (
    CollectionOperationError,
    VectorDeletionError,
    VectorIndexingError,
    VectorStoreError,
    VectorStoreProviderNotFoundError,
    VectorStoreValidationError,
)
from app.exceptions.base import AppException
from app.infrastructure.storage.exceptions import (
    StorageDeleteError,
    StorageDownloadError,
    StorageError,
    StorageListError,
    StorageNotFoundError,
    StorageUploadError,
)
from app.schemas.common import ErrorDetail, ErrorResponse

logger = structlog.get_logger()

# (status_code, error_code, user_facing_message) per domain exception type.
# Anything not listed falls back to a generic 500 for its exception family.
_RETRIEVAL_ERROR_RESPONSES: dict[type[RetrievalError], tuple[int, str, str]] = {
    RetrievalValidationError: (
        400,
        "RETRIEVAL_VALIDATION_ERROR",
        "The search request was invalid.",
    ),
    RetrievalProviderNotFoundError: (
        500,
        "RETRIEVAL_PROVIDER_NOT_FOUND",
        "Search is not available right now.",
    ),
    RetrievalExecutionError: (
        503,
        "RETRIEVAL_UNAVAILABLE",
        "Search is temporarily unavailable. Please try again.",
    ),
}

_VECTOR_STORE_ERROR_RESPONSES: dict[type[VectorStoreError], tuple[int, str, str]] = {
    VectorStoreValidationError: (
        400,
        "VECTOR_STORE_VALIDATION_ERROR",
        "The knowledge-base request was invalid.",
    ),
    VectorStoreProviderNotFoundError: (
        500,
        "VECTOR_STORE_PROVIDER_NOT_FOUND",
        "The knowledge base is not available right now.",
    ),
    CollectionOperationError: (
        503,
        "VECTOR_STORE_UNAVAILABLE",
        "The knowledge base is temporarily unavailable. Please try again.",
    ),
    VectorIndexingError: (
        503,
        "VECTOR_STORE_UNAVAILABLE",
        "The knowledge base is temporarily unavailable. Please try again.",
    ),
    VectorDeletionError: (
        503,
        "VECTOR_STORE_UNAVAILABLE",
        "The knowledge base is temporarily unavailable. Please try again.",
    ),
}

_STORAGE_ERROR_RESPONSES: dict[type[StorageError], tuple[int, str, str]] = {
    StorageNotFoundError: (
        503,
        "STORAGE_NOT_FOUND_CHECK_FAILED",
        "File storage is temporarily unavailable. Please try again.",
    ),
    StorageUploadError: (
        503,
        "STORAGE_UPLOAD_FAILED",
        "File storage is temporarily unavailable. Please try again.",
    ),
    StorageDownloadError: (
        503,
        "STORAGE_DOWNLOAD_FAILED",
        "File storage is temporarily unavailable. Please try again.",
    ),
    StorageDeleteError: (
        503,
        "STORAGE_DELETE_FAILED",
        "File storage is temporarily unavailable. Please try again.",
    ),
    StorageListError: (
        503,
        "STORAGE_LIST_FAILED",
        "File storage is temporarily unavailable. Please try again.",
    ),
}


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all application exception handlers.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ) -> JSONResponse:
        """
        Handle all custom application exceptions.
        """

        logger.warning(
            "app.exception",
            code=exc.code,
            error_message=exc.message,
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code=exc.code,
                message=exc.message,
                details=exc.details,
            )
        )

        retry_after_seconds = getattr(exc, "retry_after_seconds", None)
        headers = {"Retry-After": str(retry_after_seconds)} if retry_after_seconds else None

        return JSONResponse(
            status_code=exc.status_code,
            content=response.model_dump(),
            headers=headers,
        )

    @app.exception_handler(RetrievalError)
    async def retrieval_exception_handler(
        request: Request,
        exc: RetrievalError,
    ) -> JSONResponse:
        """
        Handle Retrieval Platform exceptions.

        Translates domain failures (bad input, misconfigured provider,
        a failed Qdrant call) into a meaningful status code and message
        instead of falling through to the generic 500 handler.
        """

        status_code, code, message = _RETRIEVAL_ERROR_RESPONSES.get(
            type(exc),
            (500, "RETRIEVAL_ERROR", "An unexpected search error occurred."),
        )

        logger.warning(
            "retrieval.exception",
            code=code,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
            )
        )

        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(VectorStoreError)
    async def vector_store_exception_handler(
        request: Request,
        exc: VectorStoreError,
    ) -> JSONResponse:
        """
        Handle Vector Store Platform exceptions.

        Mirrors retrieval_exception_handler for the vector store's own
        exception hierarchy (e.g. an owner-scoped `count()` failure).
        """

        status_code, code, message = _VECTOR_STORE_ERROR_RESPONSES.get(
            type(exc),
            (500, "VECTOR_STORE_ERROR", "An unexpected knowledge-base error occurred."),
        )

        logger.warning(
            "vector_store.exception",
            code=code,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
            )
        )

        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(StorageError)
    async def storage_exception_handler(
        request: Request,
        exc: StorageError,
    ) -> JSONResponse:
        """
        Handle object-storage (S3) exceptions.

        Mirrors retrieval_exception_handler/vector_store_exception_handler
        for the storage layer's own exception hierarchy -- without this,
        a failed upload/download/delete/presigned-URL check falls through
        to the generic 500 handler with no actionable message.
        """

        status_code, code, message = _STORAGE_ERROR_RESPONSES.get(
            type(exc),
            (500, "STORAGE_ERROR", "An unexpected file storage error occurred."),
        )

        logger.warning(
            "storage.exception",
            code=code,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code=code,
                message=message,
            )
        )

        return JSONResponse(
            status_code=status_code,
            content=response.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        Handle FastAPI validation errors.
        """

        errors = exc.errors()

        logger.warning(
            "app.validation_error",
            error_count=len(errors),
            errors=[
                {"loc": e.get("loc"), "msg": e.get("msg"), "type": e.get("type")} for e in errors
            ],
        )

        response = ErrorResponse(
            error=ErrorDetail(
                code="REQUEST_VALIDATION_ERROR",
                message="Request validation failed.",
                details={
                    "errors": errors,
                },
            )
        )

        return JSONResponse(
            status_code=422,
            content=response.model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Handle unexpected exceptions.
        """

        logger.exception("app.unhandled_exception")

        response = ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected error occurred.",
            )
        )

        return JSONResponse(
            status_code=500,
            content=response.model_dump(),
        )
