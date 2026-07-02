#!/usr/bin/env bash
set -e

echo "Running database migrations..."
uv run alembic upgrade head

echo "Checking for schema drift (model changes without a migration)..."
if ! uv run alembic check; then
  echo ""
  echo "Your SQLAlchemy models have changed but there is no migration for it yet." >&2
  echo "Generate one, review the generated file, then re-run this script:" >&2
  echo "" >&2
  echo "  uv run alembic revision --autogenerate -m \"<describe your change>\"" >&2
  echo "" >&2
  exit 1
fi

echo "Starting development server..."
uv run uvicorn app.main:app --reload
