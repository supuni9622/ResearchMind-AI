# TODO: Production deployment — AWS ECS Fargate + RDS + ElastiCache, one VPC

**Status:** Superseded as the planning document by
[`../../AWS_Deployment.md`](../../AWS_Deployment.md) and the numbered
`docs/deployment/01-06` series, which resolve most of the open questions
originally raised here (frontend hosting, secrets management, Qdrant
persistence, worker scaling/restart semantics, CI/CD shape). This file
remains as the detailed working log/checklist for implementation — treat
`AWS_Deployment.md` and `01-deployment-options-and-decisions.md` through
`06-frontend-amplify-deployment.md` as the source of truth for anything they
conflict on. Local/dev-parity containerization is done
(`docker/backend.Dockerfile`, `docker/web.Dockerfile`, full `docker-compose.yml`
— see [`../deployment/local.md`](../deployment/local.md)), which resolves this
document's biggest original blocker (no images to deploy) and de-risks the ECS
build, but no Terraform/IaC or actual AWS deployment resources exist yet.
**Source:** Deployment discussion, 2026-07-26 (updated 2026-08-26 against
`AWS_Deployment.md`). Decided against the multi-vendor serverless alternative
(Vercel + Fly.io + Neon + Upstash + Qdrant Cloud) in favor of consolidating
into AWS, since the app already depends on AWS (Cognito auth, S3
artifact/document storage, SQS processing queue) and this matches
`ROADMAP.md` Phase 9's eventual target. A hard **~$5/month persistent-cost
target** applies: ECS/Fargate, ALB, RDS, ElastiCache, NAT Gateway, and EKS are
treated as ephemeral (`terraform apply` → test/demo → `terraform destroy`),
not always-on infrastructure — see `AWS_Deployment.md` sections 23-24.

## Why this direction, and the tradeoff being accepted

Consolidating into one AWS VPC keeps auth/networking/IAM simple (no
cross-cloud credentials, no public egress between services that should be
private) and is operationally unified — one provider, one bill, one place to
reason about security groups and least-privilege access. The accepted
tradeoff: this costs more from day one than the serverless alternative (ECS
Fargate + RDS + ElastiCache have a real fixed floor even at zero traffic,
unlike Fly.io/Neon/Upstash's scale-to-zero pricing), and none of the
Dockerfiles or IaC this needs exist yet — this is greenfield infra work, not
a lift-and-shift.

## Current state (what exists today)

- `docker-compose.yml` is **dev-only** but now runs the full stack as
  containers: Postgres, Valkey, Qdrant, a `redis-stack-server` for the L2
  semantic cache, Prometheus, Grafana, the API, all four workers, and the
  Next.js frontend — see [`../deployment/local.md`](../deployment/local.md).
  `infra/observability/prometheus/prometheus.yml` now scrapes by Compose
  service name (`api:8000`, `worker-research-runtime:8010`,
  `worker-memory-lifecycle:8011`) instead of `host.docker.internal`. Those
  service-name targets still won't resolve in ECS — Fargate has no built-in
  Compose-style DNS between task definitions — so this will need
  reconfiguring to AWS Cloud Map service discovery or a static target once
  each service has its own ECS service.
- `docker/backend.Dockerfile` — one shared image for the API and all four
  `apps/worker/*_main.py` processes (they share one uv-managed dependency set
  and workers import directly from `app.*`); role is selected per-container
  via `command:`, not a separate image per process. `docker/web.Dockerfile`
  is a multi-stage Next.js `output: "standalone"` build. Both build and run
  correctly under Compose as of 2026-08-26 — this closes the "no Dockerfile
  exists" gap this document originally flagged, and the build step referenced
  in open question 5 below now exists (`docker build`/`docker compose build`),
  though nothing pushes these images to ECR yet.
- No Terraform/CloudFormation/CDK anywhere in the repo.
- Already-live AWS dependencies to carry over as-is, not rebuild: Cognito
  (auth), S3 (documents, processing/chunking/embedding/observability
  artifacts), SQS (processing queue).
- Four long-running worker processes exist today: document processing,
  Research Runtime, online evaluation scoring, and the memory lifecycle
  worker. Each needs an independently supervised compute target rather than a
  request/response one. The lifecycle worker command, configuration, and
  report-only rollout procedure are documented in
  [`docs/deployment/production.md`](../deployment/production.md#memory-lifecycle-worker).

## Target shape

- **One VPC**, public subnets for the ALB only, private subnets for
  everything else (ECS tasks, RDS, ElastiCache). Qdrant is external
  (Qdrant Cloud), not a VPC resource.
- **ECS Fargate**: one service for the API behind an ALB and independently
  supervised services/task definitions for document processing, Research
  Runtime, evaluation scoring, and memory lifecycle. The memory lifecycle
  service should use one replica; its Valkey lock protects deployment overlap,
  not horizontal scaling.
- **ECR** for API/worker/web images. `docker/backend.Dockerfile` (API +
  workers, role selected via task-definition `command:`) and
  `docker/web.Dockerfile` now exist and build successfully — what's still
  missing is a CI step to build and push them to ECR (see open question 5).
- **RDS Postgres** replacing the Compose `postgres` service.
- **ElastiCache** replacing the Compose `valkey` service (L1 exact cache,
  rate limiting, session memory) — **see open question below**, this does
  not trivially cover the L2 semantic cache's requirements.
- **Frontend (`apps/web`)**: **decided** — AWS Amplify Hosting, not ECS/Fargate.
  Keeps the existing `output: "standalone"` Next.js build, deploys
  independently of the backend, and doesn't force the ECS backend to stay up
  just to serve the UI. See
  [`../deployment/06-frontend-amplify-deployment.md`](../deployment/06-frontend-amplify-deployment.md).
- **Qdrant**: **decided** — Qdrant Cloud Free Tier, not self-hosted. AWS has
  no managed offering, and self-hosting on ECS/EC2 with EFS/EBS was rejected
  as unnecessary complexity for this project's traffic level. Do not
  implement Qdrant on ECS, EC2, EFS, or EBS. See `AWS_Deployment.md` section 3.
- **Prometheus/Grafana**: stay local-only for the first AWS iteration. Prefer
  CloudWatch logs/ECS/ALB/RDS/ElastiCache metrics for the first ECS
  implementation rather than deploying Prometheus/Grafana into ECS. Amazon
  Managed Prometheus/Grafana can be evaluated later if CloudWatch proves
  insufficient — see `AWS_Deployment.md` section 19.

## Open questions before implementing

Still genuinely open (need investigation, not just a decision):

1. **L2 semantic cache module gap.** The Compose `semantic-cache` service is
   `redis-stack-server` specifically because `langchain_redis.RedisSemanticCache`
   needs RediSearch (vector similarity) support. **Neither ElastiCache for
   Redis nor MemoryDB for Redis support Redis modules** by default, but
   `AWS_Deployment.md` section 8 directs us to run a real compatibility test
   against ElastiCache Valkey (`FT.CREATE`, `FT.SEARCH`, vector search) rather
   than assume either way — Valkey's search module support has moved since
   this gap was first flagged. Preferred outcome if compatible: one
   ElastiCache Valkey service covers L1 cache, rate limiting, session/memory,
   and semantic cache. If not compatible, options remain: self-host
   `redis-stack` on its own small ECS task (breaks the "managed ElastiCache"
   simplicity for just this one piece), or repoint the L2 semantic cache at
   Qdrant instead of Redis (a real code change in the caching platform, not
   infra-only — needs its own investigation before committing). Local Docker
   Compose keeps using Redis Stack regardless of the AWS outcome.
2. **NAT Gateway cost.** Private-subnet ECS tasks pulling images from ECR or
   calling out to Groq/OpenAI/Voyage/Tavily/LangSmith need egress — a NAT
   Gateway is one of the most commonly underestimated recurring AWS costs
   (hourly charge + per-GB processed) and is explicitly called out in
   `AWS_Deployment.md` section 7 as one of the biggest cost risks in this
   plan. Before implementing one, document why it's required, what traffic
   goes through it, and its estimated hourly/monthly cost; evaluate VPC
   endpoints for AWS-native traffic (ECR, S3, SQS, CloudWatch, Secrets
   Manager) first to cut what needs to cross the NAT path at all.

Resolved by `AWS_Deployment.md` and the `docs/deployment/01-06` series (kept
here for traceability):

3. **Worker scaling/restart semantics on Fargate.** Decided: start
   conservatively at one task per worker service (API, document, research
   runtime, evaluation, memory lifecycle all at desired count 1), using
   `research_runtime_worker.py`'s existing
   `RESEARCH_RUNTIME_WORKER_CONCURRENCY` in-process claim lanes (Postgres
   outbox, `SELECT FOR UPDATE SKIP LOCKED`) rather than defaulting to
   multiple ECS replicas everywhere. In-process concurrency and ECS
   horizontal scaling can both be used later once there's a measured
   bottleneck to scale from. Memory lifecycle stays a permanent singleton —
   its Valkey lock protects deployment overlap, not horizontal scaling. ECS
   has no built-in HTTP health check story for these long-running consumer
   loops, so restart/health must lean on process exit codes, ECS task
   restart behavior, CloudWatch logs, and application metrics rather than an
   invented HTTP endpoint. See `AWS_Deployment.md` sections 14-16.
4. **Qdrant persistence approach.** Moot — Qdrant is not self-hosted at all.
   Decided: Qdrant Cloud Free Tier, so there is no EFS-vs-EBS-on-Fargate
   tradeoff to make. See the "Qdrant" bullet above and `AWS_Deployment.md`
   section 3.
5. **CI/CD gap.** Decided direction (not yet implemented): GitHub Actions
   runs tests/lint/typecheck/frontend build/Docker build on PRs, then on
   `main` builds and pushes to ECR (`researchmind-backend`,
   `researchmind-web`, `research-intelligence-mcp` — one backend image
   reused for the API and all four workers), and CD publishes a new ECS task
   definition revision, updates the service, and verifies health. Terraform
   stays responsible for infrastructure; GitHub Actions stays responsible for
   application build/publish/deploy — these are kept as separate concerns,
   not one combined workflow. See `AWS_Deployment.md` section 25 and
   `docs/deployment/02-full-deployment-architecture.md` section 8.
6. **Frontend hosting decision.** Decided: AWS Amplify Hosting (see the
   "Frontend" bullet above).
7. **Secrets management.** Decided: AWS Secrets Manager for provider API
   keys (Groq/OpenAI/Claude/Voyage/Tavily/LangSmith), the Cognito app client
   secret, and database credentials. Never in Terraform source,
   `terraform.tfvars`, Dockerfiles, ECS task definitions as plaintext, or
   GitHub source files; non-sensitive configuration can stay as normal
   environment variables. See `AWS_Deployment.md` section 18.

## Not started

The AWS side of this is still entirely a plan, not code: no Terraform/CDK, no
ECR repos, no VPC, no RDS/ElastiCache instances, no ECS clusters/services/
task definitions exist. Of the 7 open questions originally raised here, 5 now
have a decided direction (worker scaling, Qdrant persistence, CI/CD shape,
frontend hosting, secrets management) and 2 remain genuinely open pending
investigation (semantic-cache compatibility, NAT Gateway cost) — see above.
Nothing in this document should be read as already provisioned in AWS. The
one piece that has moved from plan to code is local containerization
(Dockerfiles + Compose, see "Current state" above) — necessary groundwork for
this plan, not a substitute for it.
