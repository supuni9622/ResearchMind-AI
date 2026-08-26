variable "name_prefix" {
  type = string
}

variable "service_name" {
  description = "Short service name, e.g. \"api\" or \"worker-processing\"."
  type        = string
}

variable "cluster_id" {
  type = string
}

variable "image" {
  description = "Full ECR image URI including tag, e.g. <account>.dkr.ecr.<region>.amazonaws.com/researchmind-backend:<sha>."
  type        = string
}

variable "command" {
  description = "Override the image's default CMD (e.g. [\"python\", \"-m\", \"apps.worker.main\"] for a worker). Null keeps the image default -- used by the API, which the Dockerfile's CMD already runs correctly."
  type        = list(string)
  default     = null
}

variable "container_port" {
  description = "Null for services with no HTTP surface at all (document-processing and evaluation-scoring workers -- see docs/deployment/07-phase0-validation-findings.md section 5). Non-null registers a port mapping; only pair this with target_group_arn for the one service that's actually behind the ALB."
  type        = number
  default     = null
}

variable "target_group_arn" {
  description = "Only the API service sets this. Workers process from SQS/Postgres, not HTTP requests, and have no ALB target group."
  type        = string
  default     = null
}

variable "service_registry_arn" {
  description = "Only the MCP service (Phase 6) sets this -- an aws_service_discovery_service ARN, so the API/Research Runtime worker can reach it over Cloud Map private DNS instead of the ALB (MCP is internal-only, never internet-exposed)."
  type        = string
  default     = null
}

variable "cpu_architecture" {
  description = "\"ARM64\" (default, matches the researchmind-backend image built natively on Apple Silicon) or \"X86_64\" -- must match the actual image architecture or ECS fails to pull it (CannotPullContainerError). See this file's runtime_platform comment."
  type        = string
  default     = "ARM64"
}

variable "cpu" {
  type = number
}

variable "memory" {
  type = number
}

variable "desired_count" {
  type    = number
  default = 1
}

variable "subnet_ids" {
  description = "Public subnets -- see the Phase 0 NAT-cost decision in the vpc module for why ECS tasks live in public subnets with a locked-down security group instead of behind a NAT Gateway."
  type        = list(string)
}

variable "security_group_id" {
  type = string
}

variable "execution_role_arn" {
  type = string
}

variable "task_role_arn" {
  type = string
}

variable "environment" {
  description = "Plain (non-sensitive) environment variables."
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Map of env var name -> Secrets Manager secret ARN. Injected by ECS at container start; never appears in the task definition as plaintext."
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  type    = number
  default = 7 # short retention -- this is an ephemeral demo environment, not a compliance-retention target
}

variable "aws_region" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
