# syntax=docker/dockerfile:1
# Shared image for the API and every apps/worker/*_main.py process.
#
# One image, not three: apps/api and apps/worker are one uv-managed project
# (see pyproject.toml's single dependency set) and every worker imports
# directly from `app.*` (apps/api/app), so they cannot be packaged
# independently without duplicating the dependency install. Compose/ECS
# selects the role per-container via `command:`, not a separate image.
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

# Dependencies first so code-only changes don't invalidate this layer.
# README.md is required here too: pyproject.toml's `readme` field points at
# it, and hatchling's editable-install build validates the file exists.
COPY pyproject.toml uv.lock README.md ./
COPY apps/api/app apps/api/app
# The cache mount keeps uv's downloaded-wheel cache out of the image layer
# entirely (it's build-time-only and was previously baked in at ~5.7GB per
# build with no runtime value); it persists across builds on the host/CI
# runner instead, which also speeds up rebuilds.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

COPY alembic.ini ./
COPY alembic alembic
COPY apps/worker apps/worker

# The eval dashboard's API routes (app/services/segment_analysis.py,
# benchmark_reports.py) import the root-level `benchmarks` package and read
# `datasets/golden/...` off disk at runtime -- not dev-only tooling, so both
# must ship in this image (benchmarks/datasets and benchmarks/reports are
# the large, dev-only pieces excluded via .dockerignore).
COPY benchmarks benchmarks
COPY datasets datasets

EXPOSE 8000

# `python -m uvicorn`, not the bare `uvicorn` script: `-m` puts the working
# directory (/app) on sys.path, which is what makes `import benchmarks`
# resolve. Executing the `uvicorn` console-script directly instead puts
# .venv/bin on sys.path[0], and the `benchmarks` import above fails.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
