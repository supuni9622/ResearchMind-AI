variable "name_prefix" {
  type = string
}

variable "private_subnet_ids" {
  type = list(string)
}

variable "security_group_id" {
  description = "Security group allowing Valkey (6379) inbound from ECS tasks only."
  type        = string
}

variable "engine_version" {
  description = "Valkey 9.0+ is required for the semantic cache's TEXT+NUMERIC+VECTOR index schema -- see docs/deployment/07-phase0-validation-findings.md section 10. 8.2 only supports vector fields and would fail to create that index."
  type        = string
  default     = "9.1"
}

variable "node_type" {
  description = "Cheapest node that still supports search (t2/t3/t4g need reserved-memory-percent raised -- see main.tf)."
  type        = string
  default     = "cache.t4g.micro"
}

variable "tags" {
  type    = map(string)
  default = {}
}
