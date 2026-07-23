from fastapi import status


class AppException(Exception):
    """
    Base application exception.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        *,
        message: str,
        code: str,
        status_code: int,
        details: dict | None = None,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details

        super().__init__(message)


class NotFoundException(AppException):
    def __init__(
        self,
        message: str = "Resource not found.",
    ):
        super().__init__(
            message=message,
            code="NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ValidationException(AppException):
    def __init__(
        self,
        message: str = "Validation failed.",
        details: dict | None = None,
    ):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
        )


class ConflictException(AppException):
    def __init__(
        self,
        message: str = "Resource already exists.",
        details: dict | None = None,
    ):
        super().__init__(
            message=message,
            code="CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
            details=details,
        )


class UnauthorizedException(AppException):
    def __init__(
        self,
        message: str = "Unauthorized.",
    ):
        super().__init__(
            message=message,
            code="UNAUTHORIZED",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class RateLimitExceededException(AppException):
    def __init__(
        self,
        *,
        retry_after_seconds: int,
        message: str = "Rate limit exceeded. Please slow down.",
    ):
        self.retry_after_seconds = retry_after_seconds
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details={"retry_after_seconds": retry_after_seconds},
        )
