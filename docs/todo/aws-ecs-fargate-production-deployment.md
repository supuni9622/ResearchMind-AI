# TODO: Production deployment — AWS ECS Fargate + RDS + ElastiCache, one VPC

**Status:** Superseded as the planning document by
[`../../AWS_Deployment.md`](../../AWS_Deployment.md) and the numbered
`docs/deployment/01-06` series. Phase 0 validation
([`07-phase0-validation-findings.md`](../deployment/07-phase0-validation-findings.md))
is now complete and all 7 open questions below are resolved. This file
remains as the detailed working log/checklist for implementation — treat
`AWS_Deployment.md`, `01-deployment-options-and-decisions.md` through
`06-frontend-amplify-deployment.md`, and `07-phase0-validation-findings.md`
as the source of truth for anything they conflict on. Local/dev-parity
containerization is done
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

All 7 original open questions are now resolved — see
[`07-phase0-validation-findings.md`](../deployment/07-phase0-validation-findings.md)
for the two that needed real investigation (§§10-11 there) and
`AWS_Deployment.md`/`docs/deployment/01-06` for the rest.

1. **L2 semantic cache module gap — resolved.** A real compatibility test
   (`FT.CREATE`/`MODULE LIST` against the running local `valkey` container)
   confirmed plain OSS Valkey has zero search-module support. Checking
   AWS's current documentation, though, shows ElastiCache for Valkey 9.0
   (GA May 2026) supports the exact `TEXT`+`NUMERIC`+`VECTOR` index schema
   `langchain_redis.RedisSemanticCache` needs, at no additional cost — Valkey
   8.2 only supports vector fields and would fail to create this schema
   (`TEXT` fields are `NA` on 8.2 per AWS's own limits table). **Decision:
   target ElastiCache for Valkey 9.0** — one service covers L1 cache, rate
   limiting, session/memory, and semantic cache; no separate `redis-stack`
   ECS service needed in AWS. Local Docker Compose keeps `redis-stack-server`
   regardless, since there's no OSS Valkey image with the module built in.
2. **NAT Gateway cost — resolved.** Priced directly: a NAT Gateway is
   ~$32.40/mo fixed + $0.045/GB processed; VPC endpoints only cover
   AWS-native traffic (not Groq/OpenAI/Voyage/Tavily/LangSmith), so they
   can reduce but not eliminate the need for a NAT Gateway if ECS tasks stay
   in private subnets, and stacking enough interface endpoints across 2 AZs
   to matter (~$73/mo) is not obviously cheaper than one NAT Gateway anyway.
   **Decision: skip NAT Gateway by default.** Run ECS tasks in public
   subnets with `assign_public_ip = true` and a security group that only
   allows inbound from the ALB — RDS/ElastiCache stay in genuinely private
   subnets (they need no internet egress). NAT Gateway stays available as an
   opt-in, temporary addition during Phase 11/12 networking-learning
   sessions only, never as a standing part of `terraform apply`.

Also resolved by `AWS_Deployment.md` and the `docs/deployment/01-06` series
(kept here for traceability):

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
   `research-intelligence-mcp` — one backend image reused for the API and
   all four workers), and CD publishes a new ECS task definition revision,
   updates the service, and verifies health. `researchmind-web` has no ECR
   repository — Amplify Hosting builds the Next.js frontend directly from
   GitHub source (see Phase 2 correction below); its CI/CD is Amplify's own
   build pipeline, not a Docker push. Terraform stays responsible for
   infrastructure; GitHub Actions stays responsible for application
   build/publish/deploy — these are kept as separate concerns, not one
   combined workflow. See `AWS_Deployment.md` section 25 and
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
task definitions exist. All 7 open questions originally raised here now have
a decided direction — see above and
[`07-phase0-validation-findings.md`](../deployment/07-phase0-validation-findings.md).
Nothing in this document should be read as already provisioned in AWS. The
pieces that have moved from plan to code are local containerization
(Dockerfiles + Compose, see "Current state" above) and the Phase 0 fix to
Qdrant Cloud auth (`qdrant_api_key` was never wired into either
`AsyncQdrantClient` construction site — now fixed, see the validation
findings doc §7) — necessary groundwork for this plan, not a substitute
for it.
