variable "name_prefix" {
  type = string
}

variable "public_subnet_ids" {
  type = list(string)
}

variable "vpc_id" {
  type = string
}

variable "security_group_id" {
  type = string
}

variable "api_container_port" {
  type    = number
  default = 8000
}

variable "health_check_path" {
  description = "Liveness endpoint -- deliberately the dependency-free one (see docs/deployment/07-phase0-validation-findings.md section 5): a Postgres/Valkey/Qdrant blip shouldn't get the API task cycled by the ALB for something that isn't the API's own fault."
  type        = string
  default     = "/api/v1/health/live"
}

variable "tags" {
  type    = map(string)
  default = {}
}
