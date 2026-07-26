from fastapi import FastAPI

from app.ai.observability.prometheus.create import get_metrics_asgi_app
from app.core.settings import settings
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

    metrics_app = get_metrics_asgi_app()

    if metrics_app is not None:
        app.mount(settings.prometheus_metrics_path, metrics_app)
