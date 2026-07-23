"""
One-time provisioning for the Research Runtime's Postgres checkpoint tables.

Per ADR-032, checkpoint schema setup must never run implicitly from a request
handler or on every application start. Run this explicitly, once, against
each environment's database before enabling `research_runtime_v1_graph_enabled`:

    python scripts/provision_research_runtime_checkpoints.py

Safe to re-run: LangGraph's `AsyncPostgresSaver.setup()` is idempotent
(creates tables/indexes only if they do not already exist).
"""

import asyncio

from app.ai.runtime.research.checkpointing import provision_postgres_checkpoints
from app.core.settings import settings


async def main() -> None:
    print(f"Provisioning Research Runtime checkpoint tables for database: {settings.database_url}")
    await provision_postgres_checkpoints(settings.database_url)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
