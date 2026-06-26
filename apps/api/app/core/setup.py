from fastapi import FastAPI

from app.exceptions.handlers import register_exception_handlers
from app.middleware.register import register_middlewares


def configure_application(app: FastAPI) -> None:
    """
    Configure the FastAPI application.

    Registers middleware, exception handlers,
    and future application components.
    """

    register_middlewares(app)
    register_exception_handlers(app)
