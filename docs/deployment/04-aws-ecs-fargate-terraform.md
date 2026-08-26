# ResearchMind --- AWS ECS/Fargate + Terraform

## Purpose

This is the production-like AWS environment.

It is deliberately **ephemeral** because ResearchMind has almost no real
traffic and the persistent cost target is about \$5/month.

``` text
terraform apply
   ↓
deploy
   ↓
test / observe / scale
   ↓
terraform destroy
```

## Infrastructure

``` text
Terraform
|
+-- VPC
+-- public/private subnets
+-- routing
+-- security groups
+-- IAM
+-- ECR
+-- ECS cluster
+-- ECS task definitions/services
+-- ALB
+-- RDS
+-- ElastiCache
+-- Secrets Manager
```

## ECS services

``` text
ECS Cluster
|
+-- API / Fargate
+-- Document worker / Fargate
+-- Research Runtime worker / Fargate
+-- Evaluation worker / Fargate
+-- Memory lifecycle worker / Fargate
+-- MCP / Fargate (separate repository)
```

Initial replicas:

``` text
API                       1
Document worker           1
Research Runtime worker   1
Evaluation worker         1
Memory lifecycle worker   1
```

## API

``` text
Internet
  ↓
ALB
  ↓
ECS/Fargate API
```

Use health checks, CloudWatch logs, appropriate resource limits and
graceful shutdown.

## Workers

Workers are long-running processes, not normal HTTP services.

Use:

-   process exit status;
-   ECS restart/replacement;
-   logs;
-   application metrics.

For scaling, evaluate:

-   SQS queue depth;
-   processing latency;
-   CPU;
-   memory;
-   application concurrency.

## Data

``` text
RDS PostgreSQL
ElastiCache Valkey
S3
SQS
Qdrant Cloud Free Tier
```

Do not self-host Qdrant for this project.

## Semantic cache

Validate whether ElastiCache Valkey supports the exact operations
required by `langchain_redis.RedisSemanticCache`.

Preferred:

``` text
ElastiCache Valkey
 ├── L1 cache
 ├── rate limiting
 ├── memory/session responsibilities
 └── semantic cache
```

Only introduce another Redis Stack service if compatibility testing
proves it necessary.

## Networking

``` text
Public subnets
  └── ALB

Private subnets
  ├── ECS
  ├── RDS
  └── ElastiCache
```

Analyze VPC endpoints before NAT.

Do not create a permanent NAT Gateway without explicitly accepting its
cost.

## Secrets

Use AWS Secrets Manager for:

-   provider API keys;
-   database credentials;
-   LangSmith;
-   other sensitive configuration.

## CI/CD

``` text
GitHub
  ↓
tests/lint/typecheck/build
  ↓
Docker build
  ↓
ECR
  ↓
ECS task revision
  ↓
ECS service update
  ↓
health verification
```

Terraform remains responsible for infrastructure.

## Testing

Test:

-   Cognito authentication;
-   API;
-   document upload;
-   workers;
-   S3;
-   SQS;
-   RDS;
-   Valkey;
-   Qdrant Cloud;
-   MCP;
-   external AI providers.

Failure testing:

-   kill API task;
-   kill worker task;
-   restart MCP;
-   create queue backlog;
-   observe task replacement/recovery.

## Scaling testing

Run progressively higher workloads and observe:

-   ALB;
-   API latency;
-   CPU/memory;
-   RDS;
-   Valkey;
-   SQS depth;
-   worker concurrency;
-   Qdrant latency;
-   external provider latency.

## Cost safety

Do not leave:

-   Fargate;
-   ALB;
-   RDS;
-   ElastiCache;
-   NAT;
-   other expensive infrastructure

running unnecessarily.

Always make the destroy workflow explicit.
