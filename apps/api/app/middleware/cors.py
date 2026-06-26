from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings


def get_cors_middleware():
    return {
        "middleware_class": CORSMiddleware,
        "allow_origins": [
            settings.frontend_url,
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    }
