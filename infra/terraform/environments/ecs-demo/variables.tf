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

variable "rds_allocated_storage_gb" {
  description = "Passed to both modules/rds and modules/cloudwatch-alarms (the low-free-storage alarm threshold is relative to this) -- kept as one environment-level value instead of letting the two drift independently."
  type        = number
  default     = 20
}

# --- Phase 8: CloudWatch alarms ------------------------------------------

variable "alarm_email" {
  description = "Optional -- subscribes this address to the CloudWatch alarm SNS topic (requires confirming a subscription email from AWS after apply). Leave \"\" to still create the topic/alarms/dashboard without anyone subscribed."
  type        = string
  default     = ""
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

# CORS allow-list for the API (backend/app/middleware/cors.py splits this
# on comma). Needs BOTH localhost:3000 (local frontend dev pointed at the
# deployed backend) and the Amplify app's default domain (environments/
# frontend's `app_id` output -- https://main.<app_id>.amplifyapp.com) --
# same cross-environment plain-string-input pattern as frontend/variables.tf's
# api_url, just in the opposite direction. Update and reapply if the
# Amplify app is ever destroyed/recreated (new app_id => new domain).
variable "frontend_url" {
  description = "Comma-separated list of allowed CORS origins."
  type        = string
  default     = "http://localhost:3000,https://main.dgje0byeua4jk.amplifyapp.com"
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

# --- Phase 6: MCP ------------------------------------------------------
# research-intelligence-mcp is a separate repository (AWS_Deployment.md
# section 4) -- see section 34's manual TODO for what still needs to
# happen there before this can actually run.

variable "enable_mcp" {
  description = "Off by default -- no image exists in the research-intelligence-mcp ECR repo yet (section 34's manual TODO). Skips creating the Cloud Map namespace/service and the MCP ECS service entirely, rather than creating a service doomed to crash-loop (and burn Fargate spend) pulling a tag that doesn't exist. Flip to true once that repo has pushed a real image. The app already handles \"MCP disabled\" as a safe inert state (see .env.example's MCP_PAPERS_ENABLED comment) -- turning this off doesn't break Chat or Deep Research, paper search just stays unavailable."
  type        = bool
  default     = false
}

variable "mcp_container_port" {
  description = "Must match the vpc module's mcp_container_port (the security group rule allowing this traffic references that value, not this one -- keep them in sync)."
  type        = number
  default     = 8080
}

variable "mcp_image_tag" {
  description = "research-intelligence-mcp ECR tag to deploy. Only required when enable_mcp=true."
  type        = string
  default     = ""
}

variable "mcp_cpu" {
  description = "Unvalidated placeholder -- this repository has no visibility into the MCP server's actual resource footprint. Revisit once it's actually running (Phase 10/12)."
  type        = number
  default     = 256
}

variable "mcp_memory" {
  type    = number
  default = 512
}
