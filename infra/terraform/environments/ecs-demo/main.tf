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

  name_prefix         = local.name_prefix
  private_subnet_ids  = module.vpc.private_subnet_ids
  security_group_id   = module.vpc.rds_security_group_id
  secrets_path_prefix = var.secrets_manager_path_prefix
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
  environment = {
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
  }

  secrets = {
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
  }
}
