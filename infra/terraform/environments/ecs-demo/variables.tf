variable "aws_region" {
  description = "AWS region for the ecs-demo environment."
  type        = string
  default     = "us-east-1"
}

variable "availability_zones" {
  description = "Two AZs to spread public/private subnets across."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "private_subnet_cidrs" {
  type    = list(string)
  default = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "api_container_port" {
  type    = number
  default = 8000
}

# --- Existing AWS resources this environment references, not creates -----
# S3 and SQS already exist per AWS_Deployment.md sections 11-12 (Phase 0
# validation confirmed the SQS queue via `aws sqs list-queues`; the S3
# bucket name is the one already configured in .env). This environment's
# IAM roles are scoped to them; it does not provision or destroy them.

variable "s3_bucket_name" {
  description = "Existing S3 documents bucket name (not created by Terraform)."
  type        = string
  default     = "researchmind-ai-documents-dev"
}

variable "sqs_queue_names" {
  description = "Existing SQS queue names the ECS task role needs access to (not created by Terraform)."
  type        = list(string)
  default     = ["ResearchMind-Processing", "ResearchMind-Processing-DLQ"]
}

variable "secrets_manager_path_prefix" {
  description = "Secrets Manager name prefix this environment's secrets will be created under (Phase 3) -- the ECS execution role is scoped to read anything under this prefix."
  type        = string
  default     = "researchmind/ecs-demo"
}

# --- Phase 4: ECS API ------------------------------------------------------

variable "backend_image_tag" {
  description = "researchmind-backend ECR tag to deploy (e.g. a git short SHA). Required, no default -- ECR is immutable-tagged (modules/ecr) precisely so a deploy always names an exact, intentional image, never a silently-reused \"latest\"."
  type        = string
}

variable "api_cpu" {
  description = "Fargate vCPU units (1024 = 1 vCPU). Starting size from Phase 0's idle-memory-based estimate (docs/deployment/07-phase0-validation-findings.md section 12) -- not load-tested yet."
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Fargate memory in MB."
  type        = number
  default     = 1024
}

# Qdrant Cloud is external and not provisioned by Terraform (AWS_Deployment.md
# section 3) -- there is no default because no Qdrant Cloud cluster has been
# created yet. Must be supplied once one exists; see AWS_Deployment.md
# section 32's manual TODO.
variable "qdrant_url" {
  description = "Qdrant Cloud cluster URL, e.g. https://xxxx.us-east-1.aws.cloud.qdrant.io:6333."
  type        = string
}

# Cognito already exists (AWS_Deployment.md section 13) -- these are the
# real, non-sensitive values for this project's pool. The client secret is
# NOT here -- it's one of the Phase 3 Secrets Manager entries.
variable "cognito_user_pool_id" {
  type    = string
  default = "us-east-1_9chS0pt6P"
}

variable "cognito_app_client_id" {
  type    = string
  default = "1r4at7v1s9nr9jqots6gl15ht"
}

variable "cognito_domain" {
  type    = string
  default = "https://us-east-19chs0pt6p.auth.us-east-1.amazoncognito.com"
}
