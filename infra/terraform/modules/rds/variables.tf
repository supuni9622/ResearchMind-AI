variable "name_prefix" {
  type = string
}

variable "private_subnet_ids" {
  description = "At least two private subnet IDs, in different AZs (RDS requires a subnet group spanning >=2 AZs even for a single-AZ instance)."
  type        = list(string)
}

variable "security_group_id" {
  description = "Security group allowing Postgres (5432) inbound from ECS tasks only."
  type        = string
}

variable "engine_version" {
  description = "Postgres major version -- matches the local docker-compose `postgres:17-alpine` service. Left at major-version granularity so RDS picks the latest supported minor automatically."
  type        = string
  default     = "17"
}

variable "instance_class" {
  description = "Cheapest practical instance for a low-traffic demo environment."
  type        = string
  default     = "db.t4g.micro"
}

variable "allocated_storage_gb" {
  description = "Minimum allowed for RDS PostgreSQL gp3 storage."
  type        = number
  default     = 20
}

variable "database_name" {
  type    = string
  default = "researchmind"
}

variable "master_username" {
  type    = string
  default = "researchmind"
}

variable "tags" {
  type    = map(string)
  default = {}
}
