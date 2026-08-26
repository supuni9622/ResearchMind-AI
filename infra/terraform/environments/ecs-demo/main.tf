# Phase 1 (AWS_Deployment.md section 26): VPC, subnets, routing, security
# groups, IAM roles.
# Phase 2: ECR repositories for researchmind-backend and
# research-intelligence-mcp only -- researchmind-web has no ECR repository,
# see the module's main.tf for why.
# Phase 3: RDS PostgreSQL, ElastiCache Valkey, Secrets Manager containers.
# First resources in this environment with real ongoing cost -- see
# infra/terraform/README.md's cost table before applying.

locals {
  name_prefix = "researchmind-ecs-demo"
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

  name_prefix        = local.name_prefix
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_id  = module.vpc.rds_security_group_id
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
  # credentials aren't here -- RDS manages that secret itself.
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
