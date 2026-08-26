# Phase 1 (AWS_Deployment.md section 26): VPC, subnets, routing, security
# groups, IAM roles.
# Phase 2: ECR repositories for researchmind-backend and
# research-intelligence-mcp only -- researchmind-web has no ECR repository,
# see the module's main.tf for why.
# Phase 3: RDS PostgreSQL, ElastiCache Valkey, Secrets Manager containers.
# First resources in this environment with real ongoing cost -- see
# infra/terraform/README.md's cost table before applying.
# Phase 4: ECS cluster, API task definition/service, ALB. "Get API working
# before workers" (AWS_Deployment.md section 26) -- the four workers and
# MCP are Phase 5/6, not here yet, even though modules/ecs-service is
# already written generically enough to reuse for them.

locals {
  name_prefix = "researchmind-ecs-demo"

  sqs_queue_url = "https://sqs.${var.aws_region}.amazonaws.com/${data.aws_caller_identity.current.account_id}/${var.sqs_queue_names[0]}"

  # Cloud Map private DNS namespace name -- a plain string this config
  # owns, not a computed attribute, so it's safe to reference before the
  # namespace resource itself (used both to create it and to build
  # MCP_PAPERS_SERVER_URL below).
  service_discovery_namespace = "${local.name_prefix}.local"
  mcp_server_url              = var.enable_mcp ? "http://research-intelligence-mcp.${local.service_discovery_namespace}:${var.mcp_container_port}/mcp" : ""

  # Shared by the API and all four workers -- mirrors docker-compose.yml's
  # `x-backend-env` anchor, which every backend service (api, all workers)
  # applies identically. Same reasoning here: one shared image, one shared
  # config surface, role selected via `command` alone.
  common_environment = {
    ENVIRONMENT    = "production"
    DEBUG          = "false"
    AWS_REGION     = var.aws_region
    AWS_S3_BUCKET  = var.s3_bucket_name
    QUEUE_PROVIDER = "sqs" # NOT the .env.example default -- see Phase 0 finding section 9
    SQS_QUEUE_URL  = local.sqs_queue_url

    # One ElastiCache Valkey 9.1 instance covers L1 cache, session/memory,
    # AND the semantic cache -- see the Phase 0 semantic-cache finding
    # (docs/deployment/07-phase0-validation-findings.md section 10).
    VALKEY_URL               = "redis://${module.elasticache.endpoint}:${module.elasticache.port}/0"
    SEMANTIC_CACHE_REDIS_URL = "redis://${module.elasticache.endpoint}:${module.elasticache.port}"

    QDRANT_URL             = var.qdrant_url
    QDRANT_COLLECTION_NAME = "researchmind_knowledge"
    COGNITO_USER_POOL_ID   = var.cognito_user_pool_id
    COGNITO_APP_CLIENT_ID  = var.cognito_app_client_id
    COGNITO_DOMAIN         = var.cognito_domain

    # Chat + Deep Research (API + Research Runtime worker) reach MCP over
    # Cloud Map private DNS, never the ALB -- MCP is internal-only. Every
    # service gets this (including the two workers that never call it),
    # matching docker-compose.yml's shared `x-backend-env` -- harmless
    # unused config, same as the local setup.
    MCP_PAPERS_ENABLED        = var.enable_mcp ? "true" : "false"
    MCP_PAPERS_SERVER_URL     = local.mcp_server_url
    MCP_PAPERS_QUERY_PROVIDER = "auto"
  }

  common_secrets = {
    DATABASE_URL          = module.rds.database_url_secret_arn
    SECRET_KEY            = module.secrets.secret_arns["app-secret-key"]
    COGNITO_CLIENT_SECRET = module.secrets.secret_arns["cognito-client-secret"]
    QDRANT_API_KEY        = module.secrets.secret_arns["qdrant-api-key"]
    GROQ_API_KEY          = module.secrets.secret_arns["groq-api-key"]
    OPENAI_API_KEY        = module.secrets.secret_arns["openai-api-key"]
    ANTHROPIC_API_KEY     = module.secrets.secret_arns["anthropic-api-key"]
    VOYAGE_API_KEY        = module.secrets.secret_arns["voyage-api-key"]
    TAVILY_API_KEY        = module.secrets.secret_arns["tavily-api-key"]
    LANGSMITH_API_KEY     = module.secrets.secret_arns["langsmith-api-key"]
    MCP_PAPERS_AUTH_TOKEN = module.secrets.secret_arns["mcp-auth-token"]
  }
}

module "ecr" {
  source = "../../modules/ecr"

  repository_names = [
    "researchmind-backend",
    "research-intelligence-mcp",
  ]
}

module "vpc" {
  source = "../../modules/vpc"

  name_prefix          = local.name_prefix
  vpc_cidr             = var.vpc_cidr
  availability_zones   = var.availability_zones
  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs
  api_container_port   = var.api_container_port
  mcp_container_port   = var.mcp_container_port
}

module "iam" {
  source = "../../modules/iam"

  name_prefix   = local.name_prefix
  s3_bucket_arn = "arn:aws:s3:::${var.s3_bucket_name}"

  sqs_queue_arns = [
    for name in var.sqs_queue_names :
    "arn:aws:sqs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:${name}"
  ]

  secrets_manager_secret_arns = [
    "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.secrets_manager_path_prefix}/*",
  ]
}

module "rds" {
  source = "../../modules/rds"

  name_prefix          = local.name_prefix
  private_subnet_ids   = module.vpc.private_subnet_ids
  security_group_id    = module.vpc.rds_security_group_id
  secrets_path_prefix  = var.secrets_manager_path_prefix
  allocated_storage_gb = var.rds_allocated_storage_gb
}

module "elasticache" {
  source = "../../modules/elasticache"

  name_prefix        = local.name_prefix
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.vpc.elasticache_security_group_id
}

module "secrets" {
  source = "../../modules/secrets"

  path_prefix = var.secrets_manager_path_prefix

  # Matches the Secrets-Manager candidates from Phase 0 validation
  # (docs/deployment/07-phase0-validation-findings.md section 4). Database
  # credentials aren't here -- modules/rds owns a separate, single composed
  # DATABASE_URL secret under the same path_prefix instead (see its main.tf
  # for why).
  secret_names = [
    "groq-api-key",
    "openai-api-key",
    "anthropic-api-key",
    "voyage-api-key",
    "tavily-api-key",
    "langsmith-api-key",
    "app-secret-key",
    "cognito-client-secret",
    "qdrant-api-key",
    "mcp-auth-token", # Phase 6 -- may end up unused; see section 34's manual TODO
  ]
}

module "ecs_cluster" {
  source = "../../modules/ecs-cluster"

  name_prefix = local.name_prefix
}

module "alb" {
  source = "../../modules/alb"

  name_prefix        = local.name_prefix
  vpc_id             = module.vpc.vpc_id
  public_subnet_ids  = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.alb_security_group_id
  api_container_port = var.api_container_port
}

# Phase 7: HTTPS front door for the ALB -- see AWS_Deployment.md section
# 33 and modules/cloudfront/main.tf for why. Recreated alongside the ALB
# every ecs-demo cycle, unlike Amplify (environments/frontend), which is
# meant to outlive this environment's apply/destroy cycles.
module "cloudfront" {
  source = "../../modules/cloudfront"

  name_prefix  = local.name_prefix
  alb_dns_name = module.alb.dns_name
}

module "api_service" {
  source = "../../modules/ecs-service"

  name_prefix  = local.name_prefix
  service_name = "api"
  cluster_id   = module.ecs_cluster.cluster_id
  image        = "${module.ecr.repository_urls["researchmind-backend"]}:${var.backend_image_tag}"

  container_port   = var.api_container_port
  target_group_arn = module.alb.target_group_arn

  cpu           = var.api_cpu
  memory        = var.api_memory
  desired_count = 1

  subnet_ids         = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.ecs_tasks_security_group_id
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  aws_region         = var.aws_region

  # AWS_ACCESS_KEY_ID/SECRET_ACCESS_KEY/SESSION_TOKEN are deliberately not
  # set -- Settings treats them as optional (str | None = None), and
  # AwsSession's boto3.Session(...) with those left None falls through to
  # boto3's default credential chain, which resolves the ECS task role
  # (task_role_arn above) automatically. No static keys needed on Fargate.
  environment = local.common_environment
  secrets     = local.common_secrets
}

# --- Phase 5: workers --------------------------------------------------
# Same shared backend image, role selected via `command` -- matches
# docker-compose.yml and AWS_Deployment.md section 14. Desired count 1
# each ("start conservatively and test", section 14); memory-lifecycle
# stays a *permanent* singleton (its Valkey lock protects deployment
# overlap, not horizontal scaling -- do not raise its desired_count).
# CPU/memory from the Phase 0 idle-footprint estimate (docs/deployment/
# 07-phase0-validation-findings.md section 12): research-runtime is
# heaviest (LangGraph + embedding/reranking deps loaded at import).
# Only research-runtime and memory-lifecycle expose a port at all, and
# only for Prometheus /metrics -- neither is behind the ALB (section 5
# finding: the other two workers have zero HTTP surface, so ECS relies on
# process-exit-code task replacement instead of an invented health
# endpoint, per AWS_Deployment.md section 16).

module "worker_processing" {
  source = "../../modules/ecs-service"

  name_prefix  = local.name_prefix
  service_name = "worker-processing"
  cluster_id   = module.ecs_cluster.cluster_id
  image        = "${module.ecr.repository_urls["researchmind-backend"]}:${var.backend_image_tag}"
  command      = ["python", "-m", "apps.worker.main"]

  cpu           = 512
  memory        = 1024
  desired_count = 1

  subnet_ids         = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.ecs_tasks_security_group_id
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  aws_region         = var.aws_region

  environment = local.common_environment
  secrets     = local.common_secrets
}

module "worker_research_runtime" {
  source = "../../modules/ecs-service"

  name_prefix  = local.name_prefix
  service_name = "worker-research-runtime"
  cluster_id   = module.ecs_cluster.cluster_id
  image        = "${module.ecr.repository_urls["researchmind-backend"]}:${var.backend_image_tag}"
  command      = ["python", "-m", "apps.worker.research_runtime_main"]

  container_port = 8010 # Prometheus /metrics only -- not behind the ALB

  cpu           = 1024
  memory        = 3072
  desired_count = 1

  subnet_ids         = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.ecs_tasks_security_group_id
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  aws_region         = var.aws_region

  environment = local.common_environment
  secrets     = local.common_secrets
}

module "worker_eval_scoring" {
  source = "../../modules/ecs-service"

  name_prefix  = local.name_prefix
  service_name = "worker-eval-scoring"
  cluster_id   = module.ecs_cluster.cluster_id
  image        = "${module.ecr.repository_urls["researchmind-backend"]}:${var.backend_image_tag}"
  command      = ["python", "-m", "apps.worker.eval_scoring_main"]

  cpu           = 512
  memory        = 1024
  desired_count = 1

  subnet_ids         = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.ecs_tasks_security_group_id
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  aws_region         = var.aws_region

  environment = local.common_environment
  secrets     = local.common_secrets
}

module "worker_memory_lifecycle" {
  source = "../../modules/ecs-service"

  name_prefix  = local.name_prefix
  service_name = "worker-memory-lifecycle"
  cluster_id   = module.ecs_cluster.cluster_id
  image        = "${module.ecr.repository_urls["researchmind-backend"]}:${var.backend_image_tag}"
  command      = ["python", "-m", "apps.worker.memory_lifecycle_main"]

  container_port = 8011 # Prometheus /metrics only -- not behind the ALB

  cpu           = 512
  memory        = 1024
  desired_count = 1 # permanent singleton -- see the module comment above, do not raise

  subnet_ids         = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.ecs_tasks_security_group_id
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  aws_region         = var.aws_region

  # MEMORY_LIFECYCLE_DRY_RUN=true is already Settings' own default, but
  # set explicitly here anyway -- this is a real-deletion safety switch
  # (docs/deployment/production.md's rollout procedure is explicit: do
  # not enable real deletion until dry runs and lifecycle alerts have
  # been verified), and a safety-critical setting like that belongs in
  # infra-as-code where it's visible, not left to an implicit code
  # default someone could change later without noticing this environment
  # depends on it.
  environment = merge(local.common_environment, {
    MEMORY_LIFECYCLE_DRY_RUN = "true"
  })
  secrets = local.common_secrets
}

# --- Phase 6: MCP --------------------------------------------------------
# research-intelligence-mcp is a separate repository (AWS_Deployment.md
# section 4) -- see section 34's manual TODO for what still has to happen
# there (a Dockerfile, an image pushed to the ECR repo Phase 2 already
# created) before this can actually run.
#
# MCP is internal-only: no ALB target group, reached by the API/Research
# Runtime worker over Cloud Map private DNS instead. Classic Cloud Map
# (aws_service_discovery_*), not the newer ECS Service Connect feature --
# simpler for a one-way "API calls MCP" relationship: only MCP needs to
# register anything, callers just do a normal DNS lookup, no sidecar
# proxy required on either side.

resource "aws_service_discovery_private_dns_namespace" "internal" {
  count = var.enable_mcp ? 1 : 0

  name = local.service_discovery_namespace
  vpc  = module.vpc.vpc_id
}

resource "aws_service_discovery_service" "mcp" {
  count = var.enable_mcp ? 1 : 0

  name = "research-intelligence-mcp"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.internal[0].id

    dns_records {
      ttl  = 10
      type = "A"
    }
  }
}

module "mcp_service" {
  count = var.enable_mcp ? 1 : 0

  source = "../../modules/ecs-service"

  name_prefix  = local.name_prefix
  service_name = "mcp"
  cluster_id   = module.ecs_cluster.cluster_id
  image        = "${module.ecr.repository_urls["research-intelligence-mcp"]}:${var.mcp_image_tag}"
  # command left null -- unlike the shared backend image, this is a
  # different codebase (separate repo) with its own Dockerfile CMD; this
  # config has no basis for overriding it.

  container_port       = var.mcp_container_port
  service_registry_arn = aws_service_discovery_service.mcp[0].arn

  cpu           = var.mcp_cpu
  memory        = var.mcp_memory
  desired_count = 1

  subnet_ids         = module.vpc.public_subnet_ids
  security_group_id  = module.vpc.ecs_tasks_security_group_id
  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn
  aws_region         = var.aws_region

  # MCP's own environment/secrets needs are unknown from this repo (see
  # section 34) -- passing the same shared secrets is harmless (unused
  # entries) and gives it MCP_PAPERS_AUTH_TOKEN if it turns out to need
  # one for its own upstream paper-search providers.
  environment = local.common_environment
  secrets     = local.common_secrets
}

# Phase 8: CloudWatch alarms + dashboard (AWS_Deployment.md section 19).
# Log groups already exist per-service (modules/ecs-service); this adds
# the alarm layer on top -- ALB 5xx/unhealthy-hosts, RDS CPU/storage,
# ElastiCache engine CPU, ECS API CPU/memory. Scoped to the API service
# only, not all 5 ECS services -- see the module's variables.tf for why.
module "cloudwatch_alarms" {
  source = "../../modules/cloudwatch-alarms"

  name_prefix = local.name_prefix
  aws_region  = var.aws_region
  alarm_email = var.alarm_email

  alb_arn_suffix           = module.alb.arn_suffix
  target_group_arn_suffix  = module.alb.target_group_arn_suffix
  rds_instance_id          = module.rds.instance_id
  rds_allocated_storage_gb = var.rds_allocated_storage_gb
  elasticache_cluster_id   = module.elasticache.cluster_id
  ecs_cluster_name         = module.ecs_cluster.cluster_name
  ecs_api_service_name     = module.api_service.service_name
}
