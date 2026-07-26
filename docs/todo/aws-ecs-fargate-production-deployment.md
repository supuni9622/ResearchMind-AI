# TODO: Production deployment — AWS ECS Fargate + RDS + ElastiCache, one VPC

**Status:** Decided direction, not started. No Dockerfiles, Terraform/IaC, or
AWS deployment resources exist yet anywhere in this repo.
**Source:** Deployment discussion, 2026-07-26. Decided against the
multi-vendor serverless alternative (Vercel + Fly.io + Neon + Upstash + Qdrant
Cloud) in favor of consolidating into AWS, since the app already depends on
AWS (Cognito auth, S3 artifact/document storage, SQS processing queue) and
this matches `ROADMAP.md` Phase 9's eventual target.

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

- `docker-compose.yml` is **dev-only**: Postgres, Valkey, Qdrant, a
  `redis-stack-server` for the L2 semantic cache, Prometheus, and Grafana.
  The API itself is **not** in Compose — it runs via host `uvicorn`, and
  `infra/observability/prometheus/prometheus.yml` scrapes it via
  `host.docker.internal`. That scrape target alone won't work in ECS and
  will need reconfiguring to a service-discovery or static task-IP target.
- No `Dockerfile` exists for `apps/api`, `apps/worker`, or `apps/web`.
- No Terraform/CloudFormation/CDK anywhere in the repo.
- Already-live AWS dependencies to carry over as-is, not rebuild: Cognito
  (auth), S3 (documents, processing/chunking/embedding/observability
  artifacts), SQS (processing queue).
- Two long-running worker processes exist today
  (`apps/worker/processing_worker.py`'s consumer,
  `apps/worker/research_runtime_worker.py`) — both need an always-on
  compute target, not a request/response one.

## Target shape (sketch, not finalized)

- **One VPC**, public subnets for the ALB only, private subnets for
  everything else (ECS tasks, RDS, ElastiCache, self-hosted Qdrant).
- **ECS Fargate**: one service for the API (behind an ALB), one service (or
  two — processing worker and research-runtime worker may want independent
  scaling/restart policies) for the workers.
- **ECR** for API/worker/web images; a build step needs to exist to produce
  them (none does today).
- **RDS Postgres** replacing the Compose `postgres` service.
- **ElastiCache** replacing the Compose `valkey` service (L1 exact cache,
  rate limiting, session memory) — **see open question below**, this does
  not trivially cover the L2 semantic cache's requirements.
- **Frontend (`apps/web`)**: undecided — could stay on Vercel for
  simplicity/cost even in an otherwise-AWS setup, or move to Amplify
  Hosting / CloudFront+S3 to keep everything in one provider. Not resolved.
- **Qdrant**: AWS has no managed offering. Either self-host on an ECS
  Fargate task (or a small EC2 instance) with persistent storage (EFS or
  EBS), or accept Qdrant Cloud as the one deliberate exception to "everything
  in AWS" if self-hosting/EBS-attach-to-Fargate friction isn't worth it.
- **Prometheus/Grafana**: already containerized (`infra/observability/`);
  could run as their own small ECS services, or be swapped for Amazon
  Managed Service for Prometheus/Grafana if avoiding self-managed storage
  and upgrades is worth the extra cost.

## Open questions before implementing

1. **L2 semantic cache module gap.** The Compose `semantic-cache` service is
   `redis-stack-server` specifically because `langchain_redis.RedisSemanticCache`
   needs RediSearch (vector similarity) support. **Neither ElastiCache for
   Redis nor MemoryDB for Redis support Redis modules** — this is a real
   blocker, not a config detail. Options: self-host `redis-stack` on its own
   small ECS task/EC2 instance (breaks the "managed ElastiCache" simplicity
   for just this one piece), or repoint the L2 semantic cache at Qdrant
   instead of Redis (a real code change in the caching platform, not
   infra-only — needs its own investigation before committing).
2. **NAT Gateway cost.** Private-subnet ECS tasks pulling images from ECR or
   calling out to Groq/OpenAI/Voyage/Tavily/LangSmith need egress — a NAT
   Gateway is one of the most commonly underestimated recurring AWS costs
   (hourly charge + per-GB processed). Worth pricing explicitly against
   alternatives (VPC endpoints for AWS services at least, to cut S3/ECR/SQS
   traffic off the NAT path) before assuming "consolidated" is actually
   cheaper in practice than the serverless alternative once this is priced.
3. **Worker scaling/restart semantics on Fargate.** `research_runtime_worker.py`
   already supports `settings.research_runtime_worker_concurrency`
   in-process claim lanes (Postgres outbox, `SKIP LOCKED`) — does that mean
   one Fargate task is enough with a concurrency env var, or should this run
   as multiple tasks? Needs to be decided alongside whatever health-check /
   auto-restart policy ECS applies to a long-running consumer loop (not an
   HTTP service — ECS's default HTTP health check doesn't apply).
4. **Qdrant persistence approach.** EFS is simpler to attach to Fargate but
   slower for vector workloads; EBS is faster but doesn't attach to Fargate
   directly (would need an EC2-backed ECS capacity provider instead of pure
   Fargate for just this one service). Needs a decision, not just a
   placeholder.
5. **CI/CD gap.** `ROADMAP.md` Phase 9 already flags CI/CD as "GitHub Actions
   foundation only" — this plan needs a build-and-push-to-ECR step and a
   deploy step (ECS service update / CDK-CLI / Terraform apply) added before
   any of this is usable, not just the infra itself.
6. **Frontend hosting decision** (see sketch above) — pick one before
   writing IaC for it.
7. **Secrets management.** Where do provider API keys (Groq/OpenAI/Claude/
   Voyage/Tavily/LangSmith), the Cognito app client secret, and DB
   credentials live in this design — Secrets Manager vs. SSM Parameter
   Store vs. ECS task-definition env vars? Not decided.

## Not started

Everything here is a plan, not code. No Dockerfiles, no Terraform/CDK, no
ECR repos, no VPC, no RDS/ElastiCache instances, no ECS clusters/services/
task definitions exist. Nothing in this document should be read as already
provisioned.
