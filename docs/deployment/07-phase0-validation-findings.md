# ResearchMind — Phase 0 Validation Findings

This is the inspection required by `AWS_Deployment.md` sections 26 ("PHASE
0 — VALIDATION") and 29 ("BEFORE WRITING CODE") before any Terraform is
written. It also resolves the two remaining open questions in
[`../todo/aws-ecs-fargate-production-deployment.md`](../todo/aws-ecs-fargate-production-deployment.md).

Date: 2026-08-26. Everything below was verified against the actual running
local stack and current source, not assumed.

---

## 1. Current architecture summary

FastAPI API + 4 independently-runnable workers (document processing,
Research Runtime, evaluation scoring, memory lifecycle), one Postgres
database, Valkey, Qdrant, a dedicated Redis Stack instance for the L2
semantic cache, S3, SQS (pluggable, see §9), Cognito, Prometheus/Grafana,
LangSmith, and a separate Research Intelligence MCP process. Matches
`AWS_Deployment.md` section 1 exactly — no undocumented components found.

## 2. Docker/Compose architecture

- `docker/backend.Dockerfile` — one shared `python:3.12-slim` image for the
  API and all four `apps/worker/*_main.py` processes (single uv-managed
  dependency set; workers `import app.*` directly). Role selected via
  `command:`. Builds successfully.
- `docker/web.Dockerfile` — multi-stage Next.js `output: "standalone"`
  build. `NEXT_PUBLIC_API_URL` is a **build arg**, not a runtime env var —
  matters for ECS/Amplify: it must be baked in at image-build time, it
  cannot be swapped per-environment at container start.
- `docker-compose.yml` sets **no CPU/memory limits** on any service — Fargate
  task definitions will need explicit sizing (see §10 below); there's no
  existing resource-usage cap to carry forward as a default.
- Compose services resolve each other by service name (`postgres`,
  `valkey`, `qdrant`, `api:8000`, `worker-research-runtime:8010`,
  `worker-memory-lifecycle:8011` in `prometheus.yml`). None of this
  DNS resolves on Fargate — ECS needs Cloud Map service discovery (or static
  targets) wired up in Phase 4/5, as already flagged in the todo doc.
- A one-shot `migrate` service runs `alembic upgrade head` before API/workers
  start (`service_completed_successfully` dependency) — this ordering
  needs an ECS equivalent (a one-off migration task run before the service
  deployment, not baked into the API task's own startup).

## 3. Existing AWS dependencies

boto3-based, found in exactly three places:

- `apps/api/app/infrastructure/aws/session.py` — `AwsSession.s3()` builds a
  boto3 S3 client from `aws_region`/`aws_access_key_id`/`aws_secret_access_key`/
  `aws_session_token`, with an optional `aws_s3_endpoint_url` override (used
  for local S3-compatible testing).
- `apps/api/app/infrastructure/queue/providers/sqs.py` — `SQSQueue`, one of
  two pluggable queue backends (see §9).
- `apps/api/app/auth/providers/cognito.py` — Cognito JWT validation (see §8).

No other AWS SDK usage in the codebase.

## 4. Required environment variables

Full inventory in `.env.example`. Grouped by destination:

- **AWS-native, carry forward as-is:** `AWS_REGION`/`AI_AWS_REGION`,
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` (should
  become the ECS task role in AWS — no static keys needed there),
  `AWS_S3_BUCKET`, `AWS_S3_ENDPOINT_URL` (leave unset in AWS — it's a local
  MinIO/S3-compatible override), `QUEUE_PROVIDER`, `QS_QUEUE_URL`
  (`sqs_queue_url`), `COGNITO_USER_POOL_ID`/`COGNITO_APP_CLIENT_ID`/
  `COGNITO_DOMAIN`/`COGNITO_CLIENT_SECRET`.
- **Now also required, previously missing:** `QDRANT_API_KEY` — see §7.
- **Secrets-Manager candidates (never plaintext in a task definition):**
  `SECRET_KEY`, `COGNITO_CLIENT_SECRET`, database credentials embedded in
  `DATABASE_URL`, `VOYAGE_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `GEMINI_API_KEY`, `GROQ_API_KEY`, `TAVILY_API_KEY`, `LANGSMITH_API_KEY`,
  `MCP_PAPERS_AUTH_TOKEN`, `QDRANT_API_KEY`, `GRAFANA_ADMIN_PASSWORD`.
- **Infra-target overrides** (Compose already does this pattern for
  `DATABASE_URL`/`VALKEY_URL`/`QDRANT_URL`/`SEMANTIC_CACHE_REDIS_URL` — ECS
  task definitions need the RDS/ElastiCache/Qdrant-Cloud equivalents):
  `DATABASE_URL`, `VALKEY_URL`, `QDRANT_URL`, `SEMANTIC_CACHE_REDIS_URL`.
- Everything else (feature flags, model names, tuning thresholds, ports) is
  plain non-sensitive config and can stay as normal ECS task-definition
  environment variables.

## 5. Existing health endpoints

- API: `GET /api/v1/health/live` (liveness — no dependency checks, already
  used by the Compose `healthcheck:`), `GET /api/v1/health/ready`
  (readiness), `GET /api/v1/health` (dependency status for postgres/valkey/
  qdrant). **Recommendation:** point the ALB target-group health check at
  `/api/v1/health/live`, not the dependency-checking `/health` — using the
  dependency-aware one would mark the API task unhealthy (and get it cycled
  by ECS) on a transient Postgres/Valkey/Qdrant blip that isn't the API's own
  fault.
- Workers: only two of the four expose any HTTP surface at all, and it's
  metrics-only, not a health endpoint — `research_runtime_worker_metrics_port`
  (8010) and `memory_lifecycle_worker_metrics_port` (8011), both Prometheus
  `/metrics`. The document-processing and evaluation-scoring workers have
  **zero HTTP surface** — no port, nothing to health-check over HTTP at all.
  ECS health for all four workers must rely on process exit code / ECS task
  restart behavior, exactly as `AWS_Deployment.md` section 16 anticipates;
  don't invent an HTTP health check for the two workers that have no
  listener.

## 6. Worker commands

```text
python -m apps.worker.main                      # document processing
python -m apps.worker.research_runtime_main      # Research Runtime
python -m apps.worker.eval_scoring_main          # evaluation scoring
python -m apps.worker.memory_lifecycle_main      # memory lifecycle
```

All four run from the one shared backend image; only the ECS task
definition's `command` differs per service, matching `docker-compose.yml`.

## 7. Qdrant Cloud integration — found and fixed a real blocker

Neither Qdrant client construction site
(`apps/api/app/db/qdrant.py`, `apps/api/app/ai/knowledge/vectorstores/create.py`)
passed an `api_key` to `AsyncQdrantClient`, and `Settings` had no
`qdrant_api_key` field at all. Qdrant Cloud requires API-key auth — as
written, the app **could not have authenticated to Qdrant Cloud**, only to
an unauthenticated local/self-hosted instance. This is now fixed:

- Added `qdrant_api_key: str | None = None` to `Settings`
  (`apps/api/app/core/settings.py`).
- Both `AsyncQdrantClient(...)` call sites now pass `api_key=settings.qdrant_api_key`.
- Added `QDRANT_API_KEY=` to `.env.example`.

`mypy` passes on all three touched files; no test referenced the old client
construction signature. Local Docker Compose is unaffected (`qdrant_api_key`
defaults to `None`, and the self-hosted `qdrant` service doesn't require
auth).

## 8. Cognito integration

`apps/api/app/auth/providers/cognito.py` + `apps/api/app/auth/dependencies.py`
validate Cognito-issued JWTs server-side; `apps/api/app/services/auth.py` and
`apps/api/app/api/v1/auth.py` wire it into the API. Frontend uses the Cognito
Hosted UI. Matches `AWS_Deployment.md` section 13 — nothing to rebuild, only
callback/logout URLs need updating once Amplify's frontend URL exists.

## 9. S3/SQS integration

- **S3** is a single boto3 client (`AwsSession.s3()`), used directly — no
  surprises, no local-only assumptions beyond the optional
  `aws_s3_endpoint_url` override which should stay unset in AWS.
- **SQS is not the only queue backend — it's one of two, selected by
  `QUEUE_PROVIDER`.** `apps/api/app/infrastructure/queue/factory.py` switches
  between `QueueProvider.VALKEY` (the `.env.example` default, backed by
  `ValkeyQueue`) and `QueueProvider.SQS` (`SQSQueue`, needs `sqs_queue_url`).
  **This means "carry SQS forward" isn't passive — the AWS ECS environment
  must explicitly set `QUEUE_PROVIDER=sqs`**, or the document-processing
  worker will silently keep using Valkey as its queue instead of SQS. This
  was confirmed empirically: the local `.env` already has
  `QUEUE_PROVIDER=sqs` set, and `worker-processing` is presently
  crash-looping in the local stack (`botocore.exceptions.NoCredentialsError`)
  because no AWS credentials are configured for it locally — an expected
  result of testing the SQS path without credentials, not a code bug, and
  left as-is since it's local `.env` state, not something this task should
  silently change.

## 10. Semantic cache — ElastiCache Valkey compatibility, resolved

`AWS_Deployment.md` section 8 required a **real compatibility test**, not an
assumption either way. Performed one directly against the running local
containers:

```text
$ docker exec researchmind-valkey valkey-cli MODULE LIST
(empty)
$ docker exec researchmind-valkey valkey-cli FT.CREATE test_idx ON HASH ...
ERR unknown command 'FT.CREATE', ...

$ docker exec researchmind-semantic-cache redis-cli MODULE LIST
search  (RediSearch, v21020) ... ReJSON, RedisCompat, redisgears_2, timeseries, bf
$ docker exec researchmind-semantic-cache redis-cli FT.CREATE test_idx ON HASH ...
OK
```

**Plain Valkey 8.1.8 (the official `valkey/valkey` OSS image) has zero
search-module support** — confirms the original blocker for self-hosting
against vanilla Valkey.

Also inspected the exact index schema `langchain_redis.RedisSemanticCache`
builds (via `redisvl.extensions.cache.llm.schema.SemanticCacheIndexSchema`):
it requires a `FT.CREATE` index with **two `TEXT` fields** (prompt, response),
two `NUMERIC` fields, and one `VECTOR` field — not vector-only.

Cross-checked against AWS's current documentation (`docs.aws.amazon.com`,
fetched 2026-08-26):

| | ElastiCache Valkey 8.2 | ElastiCache Valkey 9.0 (GA May 2026) |
|---|---|---|
| Vector search | Yes | Yes |
| `TEXT` fields | **Not supported** (`NA` in AWS's own limits table) | Supported (64 text attributes/index) |
| Cost | No additional charge, all regions | No additional charge, all regions |

**Resolution: target ElastiCache for Valkey 9.0, not 8.2.** 8.2 would fail to
create `RedisSemanticCache`'s index at all (its schema needs `TEXT` fields
8.2 doesn't have); 9.0 supports the exact schema required, at no extra
licensing cost over a plain ElastiCache Valkey node. This means the
**preferred outcome in `AWS_Deployment.md` section 8 now holds**: one
ElastiCache Valkey 9.0 service can cover L1 cache, rate limiting,
session/memory, and the L2 semantic cache — no separate `redis-stack`
ECS service needed in AWS.

Caveats to carry into Terraform:
- The cheapest node types (`cache.t2/t3/t4g.micro` and `.small`) need their
  memory-reserve percentage raised (50% for micro, 30% for small) to use
  search at all — reduces usable cache memory on the cheapest instance size,
  worth sizing against actual working-set size once measured.
- `FT.CREATE`/`FT.DROPINDEX` cannot run inside a transaction or Lua/function
  script — not a concern for `langchain_redis`'s normal usage.
- Local Docker Compose keeps `redis-stack-server` regardless — there's no
  equivalent OSS Valkey Docker image with the search module built in, so
  local/AWS parity on this one piece is intentionally asymmetric (already
  documented in `AWS_Deployment.md` section 8's closing note).

This closes open question #1 in the todo doc.

## 11. NAT Gateway / VPC endpoint strategy, resolved

Priced directly against current AWS rates (`us-east-1`, fetched 2026-08-26):

| Option | Fixed cost | Data cost | Covers |
|---|---|---|---|
| NAT Gateway | ~$32.40/mo per gateway (\$0.045/hr) | $0.045/GB processed, +$0.02/GB cross-AZ | Everything (AWS + external) |
| S3 Gateway VPC endpoint | Free | Free | S3 only |
| Interface VPC endpoint (ECR, SQS, CloudWatch Logs, Secrets Manager, ...) | ~$7.30/mo per endpoint **per AZ** (\$0.01/hr) | $0.01/GB | One AWS service each |

Two things follow from these numbers:

1. **VPC endpoints cannot fully replace a NAT Gateway here.** They only cover
   AWS-native traffic. ECS tasks still need general internet egress for
   Groq, OpenAI, Voyage, Tavily, and LangSmith — none of which have a VPC
   endpoint. If ECS tasks stay in private subnets, a NAT Gateway (or
   equivalent) is unavoidable regardless of how many AWS-service endpoints
   are added.
2. **Stacking multiple interface endpoints across 2 AZs is not obviously
   cheaper than one NAT Gateway** for a low-traffic demo — 5 endpoints
   (ECR × 2 for `api`+`dkr`, SQS, CloudWatch Logs, Secrets Manager) × 2 AZs
   ≈ $73/mo fixed, more than a single NAT Gateway's ~$32.40/mo fixed floor.

**Recommendation: skip NAT Gateway by default for the ECS-demo environment.**
Run the API/worker/MCP ECS tasks in the **public** subnets with
`assign_public_ip = true` and a security group that only permits inbound
from the ALB's security group (never open to `0.0.0.0/0` for anything but
the ALB itself) — a standard, AWS-documented pattern for cost-sensitive
non-24/7 workloads. This avoids the single most commonly "forgotten and left
running" expensive resource (`AWS_Deployment.md` section 24) entirely, while
still keeping RDS and ElastiCache in genuinely private subnets (neither needs
internet egress — only VPC-internal access from the ECS security group), so
the public/private subnet separation and least-privilege security-group
learning goal is preserved for the pieces that actually benefit from it.

NAT Gateway remains available as an **opt-in, temporary** addition during the
Phase 11/12 failure/scaling-testing window specifically to practice real
private-subnet networking (`AWS_Deployment.md` section 1's networking
learning goal) — apply it, observe it, tear it down in the same session,
never leave it as a standing part of the default `terraform apply`.

This closes open question #2 in the todo doc.

## 12. CPU/memory sizing — idle baseline

`docker stats` on the current running local stack (idle, no load):

| Service | Memory (idle) | Notes |
|---|---|---|
| `api` | ~560 MiB | |
| `worker-research-runtime` | ~1.5 GiB | Heaviest — LangGraph + embedding/reranking model deps loaded at import |
| `worker-eval-scoring` | ~550 MiB | |
| `worker-memory-lifecycle` | ~580 MiB | |

CPU is negligible at idle (<0.3% each) — not a useful signal without load;
defer real CPU sizing to Phase 10 (testing)/12 (scaling tests) once the ECS
environment exists and can be exercised.

**Proposed starting Fargate sizes** (idle memory + headroom, not final —
adjust after Phase 10/12 load testing):

| Service | vCPU | Memory |
|---|---|---|
| API | 0.5 (512) | 1 GB |
| worker-processing | 0.5 (512) | 1 GB |
| worker-research-runtime | 1.0 (1024) | 3 GB |
| worker-eval-scoring | 0.5 (512) | 1 GB |
| worker-memory-lifecycle | 0.5 (512) | 1 GB |

These are conservative starting points sized to idle footprint plus
headroom, consistent with `AWS_Deployment.md` section 14's "start
conservatively and test" instruction — not a claim that they're
load-validated.

## 13. Risks/blockers for ECS deployment — summary

| # | Item | Status |
|---|---|---|
| 1 | Qdrant Cloud auth (`api_key` never wired) | **Fixed this session** — see §7 |
| 2 | `QUEUE_PROVIDER=sqs` must be explicitly set for AWS (not "carry forward" passively) | Documented — see §9, no code change needed |
| 3 | Compose service-name DNS won't resolve on Fargate | Known, deferred to Phase 4/5 (Cloud Map) |
| 4 | `NEXT_PUBLIC_API_URL` is a Next.js **build arg**, not runtime env | Known, affects Amplify build config (Phase 7) |
| 5 | No CPU/memory limits exist today to carry forward | Addressed — starting sizes proposed in §12 |
| 6 | Semantic cache on ElastiCache Valkey | **Resolved** — target Valkey 9.0, see §10 |
| 7 | NAT Gateway necessity/cost | **Resolved** — skip by default, see §11 |
| 8 | Alembic migration ordering on ECS | Known, needs a one-off migration task before service deploy (Phase 4) |

Nothing here blocks starting Phase 1 (Terraform foundation: VPC, subnets,
routing, security groups, IAM) — the two things that could have blocked
later phases (Qdrant auth, semantic-cache compatibility) are now resolved.
