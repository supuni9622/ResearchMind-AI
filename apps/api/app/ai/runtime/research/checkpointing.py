"""Postgres checkpoint construction; not wired to application startup yet."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def postgres_checkpoint_url(database_url: str) -> str:
    """Translate SQLAlchemy async URLs to the psycopg URL expected by LangGraph."""

    return database_url.replace("+asyncpg", "").replace("+psycopg", "")


@asynccontextmanager
async def postgres_checkpointer(database_url: str) -> AsyncIterator[AsyncPostgresSaver]:
    """Yield a saver with caller-owned lifecycle; never runs setup implicitly."""

    async with AsyncPostgresSaver.from_conn_string(postgres_checkpoint_url(database_url)) as saver:
        yield saver


async def provision_postgres_checkpoints(database_url: str) -> None:
    """Explicit operational provisioning path; call outside request handling."""

    async with postgres_checkpointer(database_url) as saver:
        await saver.setup()
