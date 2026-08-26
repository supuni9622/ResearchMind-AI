# Phase 1 (AWS_Deployment.md section 26): VPC, subnets, routing, security
# groups, IAM roles only. No ECS cluster/services, ALB, RDS, ElastiCache,
# or ECR yet -- those are Phase 2+ and deliberately not created here.

locals {
  name_prefix = "researchmind-ecs-demo"
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
