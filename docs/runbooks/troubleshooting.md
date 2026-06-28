# Troubleshooting

> Common development issues and their solutions.

## Status

🚧 Living document

This file grows as we encounter real issues during development.

---

## Current Issues

### Environment Variables

**Problem**

Application cannot find `.env`.

**Solution**

Use the project root as the working directory or configure `Settings` to resolve the repository root automatically.

---

---

## Alembic / Database Migrations

### Tables missing on first run

**Symptom**

Backend starts but any request that touches the database fails with:

```
sqlalchemy.exc.ProgrammingError: relation "users" does not exist
```

Sign-in appears to succeed (Cognito returns a token) but the frontend immediately redirects back to the landing page. The backend log shows a 500 on `GET /api/v1/auth/me`.

**Cause**

Alembic migrations have never been applied to this database. The `users` (and `documents`) tables do not exist yet.

**Solution**

```bash
# From the repository root
uv run alembic upgrade head
```

This creates all tables in one step. Re-running it is safe — Alembic skips revisions that have already been applied.

**Prevention**

Always start the backend via the dev script, which runs migrations first:

```bash
./scripts/dev.sh
```

Alternatively, set `AUTO_MIGRATE=true` in `.env` so the FastAPI lifespan runs migrations automatically on every startup, even when starting uvicorn directly:

```env
AUTO_MIGRATE=true
```

---

### Alembic says "head" but the table still does not exist

**Symptom**

`alembic current` reports the latest revision, but queries fail with `relation "X" does not exist`.

**Cause**

The `alembic_version` tracking table was stamped (e.g. with `alembic stamp head`) without the migration SQL actually running. The database thinks it is up to date but the tables were never created.

**Solution**

```bash
uv run alembic stamp base   # clear the false stamp
uv run alembic upgrade head # actually run every migration
```

Verify the tables exist afterwards:

```bash
psql postgresql://researchmind:researchmind@localhost:5432/researchmind -c "\dt"
```

---

### No migrations at all (`alembic current` shows nothing)

**Symptom**

`alembic current` produces no revision output — only the INFO lines from Alembic itself.

**Cause**

The database has never had `alembic upgrade` run against it. This happens on a fresh clone or after `docker compose down -v` (which wipes volumes).

**Solution**

```bash
uv run alembic upgrade head
```

---

## TODO

- [ ] Docker issues
- [ ] uv issues
- [ ] PostgreSQL issues
- [ ] Valkey issues
- [ ] Qdrant issues
- [ ] LangGraph issues
- [ ] MCP issues