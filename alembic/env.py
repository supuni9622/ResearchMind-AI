from __future__ import annotations

from logging.config import fileConfig

from app.core.settings import settings
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# -------------------------------------------------------------------------
# Alembic Configuration
# -------------------------------------------------------------------------

config = context.config

# Use the application's database configuration.
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("psycopg", "asyncpg"),
)

# Configure logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy metadata.
#
# We don't have ORM models yet.
# This will become:
#
#     from app.db.base import Base
#     target_metadata = Base.metadata
#
# in Milestone 1.3.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using an active connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    import asyncio

    asyncio.run(run_migrations_online())
