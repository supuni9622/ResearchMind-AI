# ResearchMind AWS Deployment — Architecture & Implementation Plan

We are now ready to start implementing the AWS deployment architecture for ResearchMind.

IMPORTANT:
Do not redesign the application architecture unnecessarily.
Do not replace working application components.
Do not introduce Kubernetes into the ECS implementation.
Do not self-host Qdrant.
Do not optimize for imaginary production traffic.
The goal is production-grade architecture + real infrastructure learning while keeping AWS costs extremely low.

============================================================
1. PROJECT CONTEXT
============================================================

ResearchMind AI is a production-grade AI research platform.

Current repository:

ResearchMind-AI

Current implementation:

- Next.js 15 / React 19 frontend
- FastAPI API
- 4 independently runnable workers:
  1. document processing worker
  2. Research Runtime worker
  3. online evaluation scoring worker
  4. memory lifecycle worker
- PostgreSQL
- Valkey
- Qdrant
- Redis Stack semantic cache
- S3
- SQS
- Cognito
- Prometheus
- Grafana
- LangSmith
- external AI/tool providers
- separate Research Intelligence MCP server

The local Docker containerization is already completed and verified.

Current Docker architecture:

docker/backend.Dockerfile
    -> shared backend image
    -> API and all four workers use the same image
    -> ECS/task command determines the process role

docker/web.Dockerfile
    -> Next.js standalone build

docker-compose.yml
    -> Postgres
    -> Valkey
    -> Qdrant
    -> Redis Stack semantic cache
    -> API
    -> 4 workers
    -> Next.js frontend
    -> Prometheus
    -> Grafana

Do not break the existing local Docker Compose setup.

============================================================
2. IMPORTANT DEPLOYMENT MODES
============================================================

We have explicitly decided that ResearchMind will have THREE deployment/learning modes.

------------------------------------------------------------
MODE 1 — LOCAL DEVELOPMENT
------------------------------------------------------------

This is the everyday development environment.

Everything runs locally with Docker Compose:

    Next.js
       |
    FastAPI
       |
    4 workers
       |
    Postgres
    Valkey
    Qdrant
    Redis Stack semantic cache
    Prometheus
    Grafana

Cost:

    $0

This is the primary development environment.

Do not replace this with AWS.

The current Docker Compose setup is considered the local/dev-parity implementation and should remain working.

------------------------------------------------------------
MODE 2 — AWS ECS/FARGATE PRODUCTION-LIKE TEST ENVIRONMENT
------------------------------------------------------------

This is our real AWS production architecture.

The purpose is:

- learn Terraform
- learn AWS networking
- learn ECS/Fargate
- learn ALB
- learn IAM
- learn Secrets Manager
- learn ECR
- learn ECS service/task definitions
- learn worker deployment
- learn service discovery
- learn scaling
- learn health checks
- learn CloudWatch
- perform realistic production deployment/failure/load testing

BUT:

This environment is NOT intended to run 24/7.

Because ResearchMind is a portfolio/interview project and has almost no production traffic, we cannot afford a permanently running ECS/RDS/ElastiCache environment.

The intended lifecycle is:

    terraform apply
         |
         v
    full AWS environment
         |
         v
    test / demo / load test / observe
         |
         v
    terraform destroy

Therefore:

    ECS/Fargate = ephemeral production-like environment

NOT:

    ECS/Fargate = permanent $100+ monthly environment

We have a hard target of approximately $5/month for persistent AWS usage.

Do not assume that the full ECS environment can remain running for $5/month.

------------------------------------------------------------
MODE 3 — AWS EKS/FARGATE KUBERNETES LEARNING ENVIRONMENT
------------------------------------------------------------

This is a separate learning environment.

It is NOT the primary ResearchMind production architecture.

Purpose:

- learn Kubernetes
- learn EKS
- learn Kubernetes Deployments
- learn Services
- learn ConfigMaps
- learn Secrets
- learn probes
- learn resource requests/limits
- learn horizontal scaling
- learn rolling deployments
- learn Kubernetes networking
- learn Kubernetes operational concepts
- understand EKS/Fargate
- compare Kubernetes orchestration with ECS

Lifecycle:

    terraform apply
         |
         v
    EKS + Fargate
         |
         v
    deploy ResearchMind
         |
         v
    experiment / scale / observe
         |
         v
    terraform destroy

This environment should only exist while learning/testing.

Do NOT mix EKS resources into the ECS production Terraform environment.

There should be a clear separation between:

    terraform/environments/ecs-demo

and:

    terraform/environments/eks-lab

The same ResearchMind Docker images can be used in both environments.

============================================================
3. FINAL HIGH-LEVEL ARCHITECTURE
============================================================

The primary AWS architecture is:

                         USER
                           |
                           v
                    Next.js Frontend
                           |
                           v
                    AWS Amplify
                           |
                        HTTPS
                           |
                           v
                     AWS ALB
                           |
                           v
                    ECS / Fargate
                      FastAPI API
                           |
            +--------------+--------------+
            |              |              |
            v              v              v
          RDS          ElastiCache       SQS
       PostgreSQL         Valkey           |
                                           |
                              +------------+-----------+
                              |            |           |
                              v            v           v
                         document      research      eval
                          worker        worker       worker

                    memory lifecycle worker
                           |
                           v
                         Valkey

Qdrant is NOT self-hosted in AWS.

Use:

    Qdrant Cloud Free Tier

as the managed vector database.

This is a deliberate architectural choice.

Do NOT implement:

    Qdrant on ECS
    Qdrant on EC2
    Qdrant on EFS
    Qdrant on EBS

for the current project.

The Qdrant Cloud Free Tier currently provides a small single-node cluster suitable for our low-traffic portfolio/demo environment.

Qdrant Cloud is the one deliberate external managed dependency in the otherwise AWS-centered infrastructure.

============================================================
4. SEPARATE MCP SERVER
============================================================

ResearchMind uses a separate repository:

    research-intelligence-mcp

This is NOT part of the ResearchMind backend repository.

It is a separate MCP service.

Production-like AWS architecture:

    research-intelligence-mcp
             |
             v
        Docker image
             |
             v
            ECR
             |
             v
       ECS / Fargate
             |
             v
       ResearchMind API

The ResearchMind API communicates with the MCP server through:

    MCP_PAPERS_SERVER_URL

Keep this service independently deployable.

Do not merge the MCP server into the ResearchMind backend repository.

Do not turn MCP functionality into one of the four ResearchMind workers.

============================================================
5. FRONTEND DECISION
============================================================

The frontend is:

    apps/web

It is:

    Next.js 15
    React 19
    TypeScript
    Tailwind

The current Next.js configuration uses:

    output: "standalone"

Do NOT change this to static export unless we explicitly decide to do so later.

The frontend should NOT run on ECS/Fargate.

Deploy the frontend independently using:

    AWS Amplify Hosting

The intended architecture is:

    GitHub
       |
       v
    AWS Amplify
       |
       v
    Next.js

The frontend communicates with the ECS API through HTTPS.

Production environment variables will need to be configured for:

    NEXT_PUBLIC_API_URL
    NEXT_PUBLIC_BASE_URL
    NEXT_PUBLIC_REDIRECT_URI
    Cognito-related public configuration

Cognito callback/logout URLs must be updated to the production frontend URL.

============================================================
6. AWS SERVICES WE ARE USING
============================================================

Primary AWS services:

    VPC
    ECS
    Fargate
    ECR
    ALB
    RDS PostgreSQL
    ElastiCache for Valkey
    S3
    SQS
    Cognito
    IAM
    Secrets Manager
    CloudWatch

External managed service:

    Qdrant Cloud Free Tier

Do not introduce additional AWS services unless there is a clear architectural reason.

============================================================
7. NETWORKING
============================================================

Target:

    One VPC
    Two Availability Zones

Public subnets:

    ALB only

Private subnets:

    ECS tasks
    RDS
    ElastiCache

Qdrant Cloud is external.

The initial production-like architecture should follow proper private/public subnet separation.

However, COST IS A FIRST-CLASS CONSTRAINT.

Do not automatically create a NAT Gateway without analyzing the cost.

NAT Gateway is one of the biggest recurring cost risks for this project.

We need to investigate:

    VPC endpoints for AWS services
    controlled external egress
    NAT Gateway requirements for external AI APIs

External services include:

    Groq
    OpenAI
    Voyage AI
    Tavily
    LangSmith

AWS-native services include:

    ECR
    S3
    SQS
    CloudWatch
    Secrets Manager

Use VPC endpoints where appropriate to avoid unnecessary NAT traffic/cost.

Before implementing a NAT Gateway, document:

    why it is required
    what traffic goes through it
    estimated hourly cost
    estimated monthly cost
    cheaper alternatives

Do not hide NAT Gateway cost.

============================================================
8. SEMANTIC CACHE DECISION
============================================================

The local stack currently uses:

    redis-stack-server

because:

    langchain_redis.RedisSemanticCache

requires Redis search/vector functionality.

We previously identified this as an architectural blocker for plain ElastiCache Redis/Valkey.

Before implementing a separate Redis Stack ECS service, investigate whether the current ElastiCache Valkey version and feature set can support the actual semantic-cache operations required by ResearchMind.

Specifically validate:

    FT.CREATE
    FT.SEARCH
    vector search
    required Redis data structures
    compatibility with langchain_redis.RedisSemanticCache

Do NOT assume compatibility.

Do NOT assume incompatibility.

Perform a real compatibility test.

Preferred outcome:

    ElastiCache Valkey
          |
          +-- L1 cache
          +-- rate limiting
          +-- session/memory use
          +-- semantic cache

If compatibility is proven, remove the need for a separate Redis Stack service in AWS.

If compatibility is not proven, document the result before introducing another service.

Local Docker Compose must continue using Redis Stack if required.

============================================================
9. RDS
============================================================

Replace local:

    postgres

with:

    Amazon RDS PostgreSQL

in the ECS environment.

The application already uses PostgreSQL extensively.

RDS is the canonical relational database.

Do not move relational application data to another database.

Do not redesign the data layer.

Use Terraform.

Database credentials must NOT be hardcoded.

Use:

    AWS Secrets Manager

for database credentials/secrets.

Database migrations must be handled safely.

The current local project already has Alembic migrations.

Do not invent a new migration system.

============================================================
10. ELASTICACHE
============================================================

Replace local:

    valkey

with:

    ElastiCache for Valkey

Use it for the existing Valkey responsibilities.

Do not blindly introduce Redis and Valkey as separate AWS systems.

First determine whether semantic-cache compatibility allows one Valkey service.

============================================================
11. SQS
============================================================

SQS already exists as an AWS dependency.

Carry it forward.

Do not recreate the application's queue architecture.

The document-processing pipeline already depends on asynchronous processing.

ECS workers consume/process work.

Use SQS where the existing implementation already expects it.

============================================================
12. S3
============================================================

S3 already exists.

Use the existing S3 architecture for:

    documents
    processing artifacts
    chunking/embedding artifacts
    observability artifacts
    generated artifacts where already implemented

Do not redesign storage.

Do not move document storage into EFS.

============================================================
13. COGNITO
============================================================

Cognito already exists.

Do not rebuild authentication.

Use the existing Cognito User Pool.

The API validates Cognito JWTs.

Frontend uses the Cognito Hosted UI.

Terraform should manage infrastructure that is appropriate to manage, but do not accidentally destroy or recreate the existing production/user identity pool.

Be extremely careful with Cognito state.

If the existing Cognito resources are outside Terraform, initially treat them as existing resources and reference/import them safely rather than recreating them.

============================================================
14. ECS SERVICES
============================================================

Create an ECS cluster.

API:

    researchmind-api

Workers:

    researchmind-worker-processing
    researchmind-worker-research-runtime
    researchmind-worker-eval-scoring
    researchmind-worker-memory-lifecycle

Starting desired count:

    API = 1
    processing worker = 1
    research runtime worker = 1
    evaluation worker = 1
    memory lifecycle worker = 1

Do NOT start with multiple replicas everywhere.

The Research Runtime worker already supports:

    RESEARCH_RUNTIME_WORKER_CONCURRENCY

and uses PostgreSQL outbox claiming / SELECT FOR UPDATE SKIP LOCKED.

This means:

    process concurrency
    +
    ECS horizontal scaling

can both be used.

Start conservatively and test.

Memory lifecycle:

    exactly one replica

The existing Valkey singleton lock protects deployment overlap.

Do not horizontally scale it by default.

============================================================
15. ECS API
============================================================

The API is the only request/response ECS service.

Architecture:

    Internet
       |
       v
      ALB
       |
       v
    ECS Fargate
       |
       v
    FastAPI

Use:

    health checks
    CloudWatch logs
    appropriate CPU/memory limits
    graceful shutdown
    ECS restart behavior

Do not assume ECS HTTP health checks can be applied to workers in the same way as the API.

Workers are long-running consumer processes.

Worker supervision/restart must be designed separately.

============================================================
16. WORKER HEALTH / SCALING
============================================================

For workers:

    document processing
    research runtime
    evaluation scoring
    memory lifecycle

do not invent HTTP health endpoints unless the application actually supports them.

ECS needs a sensible way to determine task/process failure.

Use:

    process exit codes
    ECS task health/restart behavior
    CloudWatch logs
    application metrics

where appropriate.

For queue-driven workloads, scaling should eventually consider:

    SQS queue depth
    processing latency
    CPU
    memory

Do not implement sophisticated autoscaling before the basic service is working.

============================================================
17. ECR
============================================================

Create ECR repositories for:

    researchmind-backend
    research-intelligence-mcp

researchmind-web does NOT need an ECR repository. AWS Amplify Hosting for a
Next.js app builds directly from the connected GitHub source using its own
build environment -- it never pulls a pre-built Docker image from ECR. The
Docker-image-via-ECR path in Amplify's own docs refers to a different,
older feature (Amplify's multi-container Fargate hosting), which is not
what section 5's decision uses and would contradict "the frontend should
NOT run on ECS/Fargate." docker/web.Dockerfile remains real and necessary
for local Docker Compose dev-parity; it has no role in the AWS deployment
path.

The backend repository uses one image for:

    API
    all four workers

The ECS task definition determines the command.

Do not create five backend images unless there is a demonstrated reason.

============================================================
18. SECRETS
============================================================

Use AWS Secrets Manager for actual secrets.

Examples:

    GROQ_API_KEY
    OPENAI_API_KEY
    ANTHROPIC/CLAUDE credentials if used
    VOYAGE_API_KEY
    TAVILY_API_KEY
    LANGSMITH_API_KEY
    database credentials
    other sensitive provider credentials

Do NOT put secrets into:

    Terraform source
    terraform.tfvars committed to git
    Dockerfiles
    ECS task definitions as plaintext
    GitHub source files

Non-sensitive configuration can remain normal environment variables.

============================================================
19. OBSERVABILITY
============================================================

Local development keeps:

    Prometheus
    Grafana

The local dashboards are already implemented.

For the first AWS implementation, prefer:

    CloudWatch logs
    ECS metrics
    ALB metrics
    RDS metrics
    ElastiCache metrics

Do not immediately deploy Prometheus + Grafana into ECS unless there is a clear need.

Do not create unnecessary observability infrastructure.

Later we can evaluate:

    Amazon Managed Prometheus
    Amazon Managed Grafana

============================================================
20. TERRAFORM STRUCTURE
============================================================

Create a clean Terraform structure.

Suggested:

infra/
  terraform/
    modules/
      vpc/
      iam/
      ecr/
      ecs/
      alb/
      rds/
      elasticache/
      secrets/
      s3/
      sqs/

    environments/
      ecs-demo/
        main.tf
        variables.tf
        outputs.tf
        terraform.tfvars.example

      eks-lab/
        ...

Do not create unnecessary modules.

Use modules where they provide meaningful reuse.

The ECS environment and EKS environment MUST be separated.

============================================================
21. ECS DEMO ENVIRONMENT
============================================================

The ECS environment is our production-like architecture.

Expected lifecycle:

    terraform apply
    |
    deploy
    |
    test
    |
    observe
    |
    scale
    |
    failure testing
    |
    terraform destroy

We should be able to demonstrate:

    API deployment
    worker deployment
    MCP deployment
    database connectivity
    Valkey connectivity
    SQS processing
    S3 access
    Qdrant Cloud access
    Cognito authentication
    external AI APIs
    CloudWatch logs
    ECS task restart
    worker failure/recovery
    scaling

This is the environment we will use for portfolio/interview demonstrations.

============================================================
22. EKS LAB ENVIRONMENT
============================================================

Do NOT implement this as part of the first ECS deployment.

EKS is a separate learning track.

Architecture:

    Terraform
       |
       v
    EKS cluster
       |
       v
    EKS Fargate profiles
       |
       v
    Kubernetes
       |
       +-- Deployment: API
       +-- Deployment: document worker
       +-- Deployment: research worker
       +-- Deployment: eval worker
       +-- Deployment: memory worker
       +-- MCP service/deployment
       +-- Kubernetes Services
       +-- ConfigMaps
       +-- Secrets
       +-- probes
       +-- resource requests/limits

Use the SAME Docker images built for ECS.

The purpose is to compare:

    ECS/Fargate
vs
    Kubernetes/EKS/Fargate

Do not unnecessarily duplicate application implementation.

Terraform should be able to create the EKS learning environment and destroy it afterwards.

============================================================
23. COST CONSTRAINT
============================================================

HARD CONSTRAINT:

    approximately $5/month maximum persistent AWS spend

ResearchMind is NOT a business product with real production traffic.

This is an AI engineering portfolio/project.

Therefore:

Permanent/low-cost services should be limited to things such as:

    Cognito
    S3
    SQS
    ECR
    IAM
    minimal CloudWatch
    Qdrant Cloud Free Tier

Expensive compute infrastructure should NOT remain running continuously.

Especially:

    ECS Fargate
    ALB
    RDS
    ElastiCache
    NAT Gateway
    EKS

must be treated as ephemeral/demo/learning infrastructure unless we explicitly decide otherwise.

The system must make it difficult to accidentally leave expensive resources running.

Document cost risks prominently.

============================================================
24. COST SAFETY
============================================================

Add documentation for:

    terraform apply
    terraform destroy

and make the destroy workflow obvious.

Document the most dangerous forgotten resources:

    NAT Gateway
    ALB
    RDS
    ElastiCache
    Fargate tasks
    EKS cluster

Before applying expensive resources, provide an estimated cost.

Do NOT claim the entire AWS architecture costs $5/month while running continuously.

The $5 constraint applies to our realistic persistent usage.

============================================================
25. CI/CD
============================================================

Eventually implement:

GitHub
   |
   v
tests
   |
   v
lint/typecheck
   |
   v
Docker build
   |
   v
ECR
   |
   v
ECS deployment

The backend Docker image should be built once and reused for:

    API
    processing worker
    research worker
    evaluation worker
    memory worker

The frontend image can be built separately.

MCP has its own repository and CI/CD lifecycle.

Terraform infrastructure deployment should remain separate from application image deployment.

Do not combine every concern into one giant GitHub Actions workflow.

============================================================
26. IMPLEMENTATION ORDER
============================================================

Do NOT immediately create the whole AWS infrastructure.

Work in this order:

PHASE 0 — VALIDATION

1. Inspect current Dockerfiles.
2. Inspect docker-compose.yml.
3. Inspect existing AWS integration.
4. Inspect current environment variables.
5. Inspect existing Cognito/S3/SQS usage.
6. Validate ElastiCache Valkey semantic-cache compatibility.
7. Decide NAT/VPC endpoint strategy.
8. Confirm Qdrant Cloud integration.
9. Determine minimum CPU/memory requirements for API/workers.
10. Document findings.

PHASE 1 — TERRAFORM FOUNDATION

Create:

    provider
    backend/state strategy
    VPC
    subnets
    route tables
    security groups
    IAM roles

Do not create ECS services yet.

PHASE 2 — ECR

Create ECR repositories.

Build/push:

    backend
    web
    MCP

PHASE 3 — DATA LAYER

Create/configure:

    RDS PostgreSQL
    ElastiCache Valkey
    S3
    SQS
    Secrets Manager

Qdrant remains Qdrant Cloud Free Tier.

PHASE 4 — ECS API

Create:

    ECS cluster
    task definition
    API service
    ALB
    target group
    listener
    health check

Get API working before workers.

PHASE 5 — WORKERS

Deploy:

    document worker
    research runtime worker
    evaluation worker
    memory lifecycle worker

Start with one task each.

PHASE 6 — MCP

Deploy:

    research-intelligence-mcp

as a separate ECS service.

Connect ResearchMind API to it.

PHASE 7 — FRONTEND

Deploy Next.js through:

    AWS Amplify

Configure:

    API URL
    Cognito callback
    Cognito logout
    production frontend URL

PHASE 8 — OBSERVABILITY

CloudWatch logs/metrics.

Verify:

    API
    workers
    ALB
    RDS
    Valkey
    ECS

PHASE 9 — CI/CD

GitHub Actions:

    test
    build
    push ECR
    deploy ECS

PHASE 10 — TESTING

Test:

    authentication
    API
    document upload
    document processing
    retrieval
    chat
    Linear Research
    Deep Research
    MCP paper search
    worker processing
    generated report
    S3
    SQS
    database
    cache

PHASE 11 — FAILURE TESTING

Deliberately:

    kill API task
    kill worker task
    stop/restart MCP
    introduce queue backlog
    test worker restart
    test API restart
    test database connectivity failure

Observe recovery.

PHASE 12 — SCALING TESTS

Test progressively:

    low traffic
    moderate traffic
    high traffic

Observe:

    ALB
    ECS
    CPU
    memory
    RDS
    Valkey
    SQS
    worker concurrency
    external API latency

============================================================
27. DOCUMENTATION REQUIREMENT
============================================================

Every architectural decision should be documented.

Create/update:

    docs/deployment/aws-architecture.md

and document:

    Local mode
    ECS/Fargate mode
    EKS/Fargate mode

Also document why:

    Qdrant Cloud Free Tier
    Amplify
    ECS/Fargate
    RDS
    ElastiCache
    SQS
    S3
    Secrets Manager
    Terraform

were selected.

Document rejected alternatives:

    Vercel
    self-hosted Qdrant
    ECS + EC2
    EKS production
    permanent Fargate
    permanent NAT Gateway

only where relevant.

============================================================
28. IMPORTANT ENGINEERING PRINCIPLE
============================================================

Do not over-engineer.

This project exists to demonstrate:

    AI engineering
    production architecture
    cloud infrastructure
    containers
    Terraform
    orchestration
    scaling
    reliability
    observability
    security

It does NOT exist to demonstrate:

    maximum AWS complexity.

Every infrastructure component must have a reason.

If a simpler architecture provides the same learning/product value, choose the simpler architecture.

============================================================
29. BEFORE WRITING CODE
============================================================

First inspect the existing repository and produce:

1. Current architecture summary
2. Existing Docker/Compose architecture
3. Existing AWS dependencies
4. Required environment variables
5. Existing health endpoints
6. Worker commands
7. MCP integration
8. Current Cognito integration
9. Current S3/SQS integration
10. Risks/blockers for ECS deployment

Then propose the exact Terraform implementation plan.

DO NOT start creating Terraform resources until this inspection is complete.

We will review the plan before the first terraform apply.

============================================================
30. FINAL ARCHITECTURAL DECISION
============================================================

The architecture we are converging on is:

LOCAL:

    Docker Compose
    $0

AWS PRODUCTION-LIKE:

    Amplify
       |
    ALB
       |
    ECS/Fargate API
       |
    +-- ECS/Fargate worker-processing
    +-- ECS/Fargate worker-research
    +-- ECS/Fargate worker-evaluation
    +-- ECS/Fargate worker-memory
       |
    RDS PostgreSQL
    ElastiCache Valkey
    SQS
    S3
    Secrets Manager
    Cognito
    Qdrant Cloud Free Tier
    separate ECS/Fargate MCP server

    Managed through Terraform.

    Apply -> test -> destroy.

KUBERNETES LEARNING:

    Terraform
       |
    EKS
       |
    Fargate
       |
    Kubernetes
       |
    same ResearchMind Docker images

    Apply -> learn/test -> destroy.

ECS and EKS are separate environments.

Do not mix them.

============================================================
31. SUCCESS CRITERIA
============================================================

We are successful when:

[x] Local Docker Compose still works.

[x] ResearchMind backend builds successfully.

[x] Frontend builds successfully.

[ ] MCP builds successfully.

[x] ECR repositories exist.

[x] Terraform can create the AWS environment.

[ ] API runs on ECS/Fargate.

[ ] All four workers run independently.

[ ] MCP runs independently.

[ ] RDS works.

[ ] ElastiCache works.

[ ] SQS works.

[ ] S3 works.

[ ] Cognito authentication works.

[ ] Qdrant Cloud works.

[ ] Frontend runs through Amplify.

[ ] Secrets are not hardcoded.

[ ] CloudWatch provides useful logs/metrics.

[ ] Terraform destroy removes expensive infrastructure.

[ ] ECS environment can be recreated from scratch.

[ ] Same application can later be deployed to EKS/Fargate.

[x] Architecture and tradeoffs are documented.

Most importantly:

The deployment should demonstrate genuine production engineering knowledge without creating unnecessary cloud complexity or violating the project's ~$5/month persistent-cost constraint.

One thing I'd add to this plan

I would make the three modes visually explicit in the repository, because this will help you later when you're learning and also when explaining ResearchMind in an interview:

ResearchMind
│
├── Local Development
│   └── Docker Compose
│
├── AWS Production-like
│   ├── Terraform
│   ├── ECS
│   └── Fargate
│
└── Kubernetes Learning Lab
    ├── Terraform
    ├── EKS
    └── Fargate

The key concept is:

Mode	Purpose	Lifecycle	Cost target
Local	Daily development	Always available locally	$0
ECS + Fargate	Production architecture/demo	apply → test → destroy	Ephemeral
EKS + Fargate	Kubernetes learning	apply → learn → destroy	Ephemeral

And Qdrant Cloud Free Tier sits outside all three compute environments:

                ResearchMind
                     │
        ┌────────────┼────────────┐
        │            │            │
      Local         ECS          EKS
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
             Qdrant Cloud
              Free Tier

============================================================
32. MANUAL TODO — BEFORE FIRST END-TO-END TEST
============================================================

Not automated on purpose (real AWS cost, real secret values, a real
external account). Do these only when actually ready to test the ecs-demo
environment end-to-end.

[ ] 1. Create a Qdrant Cloud Free Tier cluster (AWS_Deployment.md section 3
       -- Qdrant is external, Terraform does not provision it). Note the
       cluster URL and API key; the API key becomes the
       `qdrant-api-key` secret value in step 3 below, the URL becomes the
       `qdrant_url` Terraform variable in step 2.

[ ] 2. Apply Phase 3 + 4 + 5 together (RDS, ElastiCache, Secrets Manager
       containers, ECS cluster, API service, ALB, all four worker
       services) -- applying Phase 3 alone first would pay for
       RDS/ElastiCache with nothing yet able to connect to them:

    cd infra/terraform/environments/ecs-demo
    AWS_PROFILE=researchmind-deploy terraform apply \
      -var="backend_image_tag=bc623c6" \
      -var="qdrant_url=<your Qdrant Cloud cluster URL>"

    Expect 36 resources to add: RDS+ElastiCache+9 secrets (17), ECS
    cluster+ALB+API service (7), 4 worker services (12). Starts real
    ongoing cost (~$21-27/month RDS+ElastiCache, plus ALB/Fargate billing
    for 5 running tasks -- see infra/terraform/README.md's cost table).
    `backend_image_tag` must be an existing tag in the researchmind-backend
    ECR repo (currently `bc623c6`; push a new one first if the code has
    moved on -- the SAME tag deploys to all 5 services, one shared image).
    Run `terraform destroy` when done testing.

[ ] 3. Populate the 9 Secrets Manager containers Phase 3 created (real
       values, never through Terraform/tfstate) -- the API and all four
       workers won't start cleanly until these have real values, since
       every one of their task definitions already references all of them
       (same shared environment/secrets, see main.tf's `local.common_secrets`):

    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/groq-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/openai-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/anthropic-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/voyage-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/tavily-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/langsmith-api-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/app-secret-key --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/cognito-client-secret --secret-string "<value>"
    AWS_PROFILE=researchmind-deploy aws secretsmanager put-secret-value \
      --secret-id researchmind/ecs-demo/qdrant-api-key --secret-string "<value>"

    RDS's DATABASE_URL secret is NOT in this list -- Terraform generates
    and owns that value itself (modules/rds), you never touch it.

    After populating secrets, force a fresh deployment on all five
    services so they pick up the new values (ECS resolves secrets once
    per task, not continuously):

    for svc in api worker-processing worker-research-runtime worker-eval-scoring worker-memory-lifecycle; do
      AWS_PROFILE=researchmind-deploy aws ecs update-service \
        --cluster researchmind-ecs-demo-cluster \
        --service "researchmind-ecs-demo-$svc" \
        --force-new-deployment --region us-east-1
    done

[ ] 4. Verify the API: `curl http://$(cd infra/terraform/environments/ecs-demo && AWS_PROFILE=researchmind-deploy terraform output -raw api_url | sed 's#http://##')/api/v1/health/live`
       (HTTP only -- see modules/alb/main.tf; not yet safe for the Amplify
       frontend, which is HTTPS, to call -- that needs Phase 7 to resolve
       the custom-domain/ACM gap first). Verify the workers by checking
       CloudWatch Logs (`/ecs/researchmind-ecs-demo-worker-*`) or, for
       research-runtime/memory-lifecycle, hitting their `/metrics` port
       directly if reachable.

Until all steps are done, Phase 3+4+5 stay as validated-but-unapplied
Terraform code (see infra/terraform/README.md "Current status").
