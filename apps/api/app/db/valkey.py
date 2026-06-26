import redis.asyncio as redis

from app.core.settings import settings


def create_valkey_client() -> redis.Redis:
    """
    Create the application's Valkey client.

    The client is created during FastAPI startup
    and closed during shutdown.
    """

    return redis.from_url(
        settings.valkey_url,
        decode_responses=True,
    )
