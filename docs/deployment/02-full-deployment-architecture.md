# ResearchMind --- Full Deployment Infrastructure Architecture

## 1. Final architecture

``` text
                         USER
                           |
                           v
                AWS Amplify / Next.js
                           |
                         HTTPS
                           |
                           v
                    Application ALB
                           |
                           v
                  ECS / Fargate API
                           |
          +----------------+----------------+
          |                |                |
          v                v                v
       RDS PG        ElastiCache          SQS
                        Valkey              |
                                            +--> document worker
                                            +--> research worker
                                            +--> evaluation worker

                  memory lifecycle worker
                           |
                         Valkey

                  API <----> Qdrant Cloud
                  API <----> MCP / ECS Fargate

              Existing AWS dependencies:
              Cognito + S3 + SQS

              ECR → API/workers/MCP images
              Secrets Manager → task secrets
              CloudWatch → logs/metrics
```

Qdrant is intentionally **Qdrant Cloud Free Tier**, not self-hosted.

## 2. Networking

``` text
Internet
   |
   v
Public subnets
   |
   +--> ALB
          |
          v
Private subnets
   |
   +--> ECS/Fargate
   +--> RDS
   +--> ElastiCache
```

Target:

-   one VPC;
-   two Availability Zones;
-   ALB in public subnets;
-   ECS/RDS/ElastiCache in private subnets;
-   security groups enforce access;
-   evaluate VPC endpoints for AWS-native traffic;
-   do not create NAT blindly because it is a major recurring cost.

External providers such as Groq, OpenAI, Voyage, Tavily and LangSmith
require controlled egress.

## 3. Application services

### API

One FastAPI ECS/Fargate service behind the ALB.

### Workers

Four independently supervised ECS/Fargate services:

1.  document processing;
2.  Research Runtime;
3.  online evaluation scoring;
4.  memory lifecycle.

Initial desired count:

  Service               Replicas
  ------------------- ----------
  API                          1
  Document worker              1
  Research Runtime             1
  Evaluation worker            1
  Memory lifecycle             1

Memory lifecycle remains singleton.

## 4. MCP

The `research-intelligence-mcp` repository remains independent:

``` text
GitHub → Docker → ECR → ECS/Fargate → ResearchMind API
```

It is not merged into the four ResearchMind workers.

## 5. Data

  -----------------------------------------------------------------------
  Concern                 Local                   AWS
  ----------------------- ----------------------- -----------------------
  Relational DB           Postgres container      RDS PostgreSQL

  L1/cache/locking        Valkey container        ElastiCache Valkey

  Vector DB               Qdrant container        Qdrant Cloud Free Tier

  Semantic cache          Redis Stack             Validate ElastiCache
                                                  Valkey compatibility

  Objects                 S3 integration          Existing S3

  Queue                   SQS integration         Existing SQS

  Auth                    Cognito                 Existing Cognito
  -----------------------------------------------------------------------

## 6. Security

-   Existing Cognito remains the identity provider.
-   Use least-privilege IAM task roles.
-   Store provider/API/database secrets in AWS Secrets Manager.
-   Do not place secrets in source, Dockerfiles, Terraform code or
    plaintext task definitions.
-   Keep RDS/Valkey private.

## 7. Observability

Local:

``` text
Prometheus + Grafana
```

AWS first stage:

``` text
CloudWatch Logs
ECS metrics
ALB metrics
RDS metrics
ElastiCache metrics
```

Managed Prometheus/Grafana can be evaluated later.

## 8. CI/CD

### CI

``` text
Pull Request
   ↓
Tests
   ↓
Lint/type-check
   ↓
Frontend build
   ↓
Docker build
```

### Image publishing

``` text
main
 ↓
build
 ↓
ECR
```

Repositories:

``` text
researchmind-backend
research-intelligence-mcp
```

`researchmind-web` is not an ECR repository -- Amplify Hosting builds the
Next.js frontend directly from GitHub source, not from a pushed Docker
image (see `06-frontend-amplify-deployment.md`).

### CD

``` text
ECR image
   ↓
new ECS task definition revision
   ↓
ECS service update
   ↓
health verification
```

Terraform owns infrastructure. GitHub Actions owns application
build/publish/deployment.

## 9. Reliability and scalability

Reliability mechanisms:

-   ALB health checks;
-   ECS task replacement;
-   independent worker services;
-   SQS-based asynchronous processing;
-   PostgreSQL transactional work claiming;
-   Valkey singleton locking;
-   managed RDS/ElastiCache;
-   CloudWatch logs/metrics;
-   independent MCP service;
-   Terraform reproducibility.

Scaling mechanisms:

``` text
API → ECS desired count/autoscaling
Workers → concurrency + task count
Queue workloads → SQS depth/latency
Database → RDS capacity/connections
Cache → ElastiCache capacity
```

Scale from measured bottlenecks, not by defaulting every service to
multiple replicas.

## 10. Cost strategy

Hard persistent target:

``` text
~$5/month
```

Therefore expensive resources are not kept running continuously:

-   Fargate;
-   ALB;
-   RDS;
-   ElastiCache;
-   NAT Gateway;
-   EKS.

Workflow:

``` text
terraform apply
      ↓
deploy
      ↓
test / load test / failure test
      ↓
terraform destroy
```

Low-cost/persistent candidates include IAM, Cognito, S3, SQS, ECR,
minimal CloudWatch and Qdrant Cloud Free Tier.

## 11. Deployment modes

``` text
MODE 1
Local
Docker Compose
$0

MODE 2
AWS production-like
Terraform → ECS/Fargate
apply → test → destroy

MODE 3
Kubernetes learning
Terraform → EKS/Fargate
apply → learn/test → destroy
```

The same application/container images are intentionally reusable across
ECS and EKS.
