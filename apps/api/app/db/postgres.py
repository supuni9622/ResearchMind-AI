#Database engine
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from app.core.settings import settings

# What does Engine do?

# 1. creates connections
# 2. reuses connections
# 3. manages the connection pool
# 4. reconnects
# 5. handles transactions

# It's basically "The database manager."

engine: AsyncEngine = create_async_engine(
    settings.database_url.replace("psycopg", "asyncpg"),
    echo=settings.environment == "development",
    future=True,
    pool_pre_ping=True,
)