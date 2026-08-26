variable "name_prefix" {
  description = "Prefix applied to every resource name/tag created by this module (e.g. \"researchmind-ecs-demo\")."
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "Exactly two AZs to spread public/private subnets across."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "AWS_Deployment.md targets two Availability Zones -- pass exactly two."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for the public subnets (one per AZ). Holds the ALB and, per the Phase 0 NAT-cost decision, the ECS tasks themselves."
  type        = list(string)
  default     = ["10.20.0.0/24", "10.20.1.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for the private subnets (one per AZ). Holds RDS and ElastiCache only -- neither needs internet egress, so these subnets have no NAT/IGW route at all."
  type        = list(string)
  default     = ["10.20.10.0/24", "10.20.11.0/24"]
}

variable "api_container_port" {
  description = "Port the API task listens on -- the only inbound path the ALB security group is allowed to reach on ECS tasks."
  type        = number
  default     = 8000
}

variable "mcp_container_port" {
  description = "Port the internal-only MCP service (Phase 6) listens on -- reachable from other ECS tasks in the same security group via Cloud Map, never through the ALB."
  type        = number
  default     = 8080
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
