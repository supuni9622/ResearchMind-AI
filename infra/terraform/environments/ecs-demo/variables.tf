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
