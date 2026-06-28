import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.base import AppException
from app.schemas.common import ErrorDetail, ErrorResponse

logger = structlog.get_logger()


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

        return JSONResponse(
            status_code=exc.status_code,
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
