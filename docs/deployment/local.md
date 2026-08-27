# Local Deployment

> Running the complete ResearchMind platform locally.

## Status

✅ Complete — full stack runs via `docker compose up -d --build`. See the
[README's "Full Stack via Docker Compose" section](../../README.md#full-stack-via-docker-compose)
for the exact commands and a host-run alternative for hot-reload development.

---

## Architecture

Every service below runs as its own Compose container:

- FastAPI (`api`)
- Next.js (`web`)
- PostgreSQL (`postgres`)
- Valkey (`valkey`)
- Qdrant (`qdrant`)
- Semantic-cache Redis (`semantic-cache`)
- Four workers: document processing, Research Runtime, evaluation scoring,
  memory lifecycle
- Prometheus + Grafana

`docker/backend.Dockerfile` is one shared image for the API and all four
workers (`apps/api` and `apps/worker` are a single uv-managed project;
workers import directly from `app.*`); `docker/web.Dockerfile` builds the
Next.js frontend using `output: "standalone"`. A `migrate` service runs
`alembic upgrade head` once before the API/workers start.

The Research Intelligence MCP server (paper search) still runs as its own
separate process outside this Compose file — see README step 11.

---

## Current Deployment

Available today, all as Compose services:

- Backend API + Next.js frontend
- PostgreSQL, Valkey, Qdrant, semantic-cache Redis
- All four workers (processing, Research Runtime/LangGraph, eval scoring,
  memory lifecycle)
- Prometheus + Grafana

This is the local/dev-parity stack, not the production target — see
[`03-local-development-docker.md`](03-local-development-docker.md) for how
this local stack relates to the AWS ECS/Fargate and EKS/Fargate modes,
[`production.md`](production.md) for the production architecture, and
[`../todo/aws-ecs-fargate-production-deployment.md`](../todo/aws-ecs-fargate-production-deployment.md)
for the implementation checklist.

---

## TODO

- [x] Backend
- [x] Frontend
- [x] Worker
- [x] LangGraph
- [ ] MCP Integration (paper search server still runs outside Compose)
- [x] Monitoring