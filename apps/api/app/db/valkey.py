#Valkey client
import redis.asyncio as redis
from app.core.settings import settings

client = redis.from_url(
    settings.valkey_url,
    decode_responses=True,
)