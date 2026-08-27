variable "name_prefix" {
  type = string
}

variable "aws_region" {
  type = string
}

variable "alarm_email" {
  description = "Optional -- subscribes this address to the SNS alarm topic (requires confirming a subscription email from AWS). Leave \"\" to still create the topic/alarms (visible in the CloudWatch console, useful during Phase 11/12 failure/scaling testing) without anyone subscribed."
  type        = string
  default     = ""
}

variable "alb_arn_suffix" {
  type = string
}

variable "target_group_arn_suffix" {
  type = string
}

variable "rds_instance_id" {
  type = string
}

variable "rds_allocated_storage_gb" {
  description = "Used to size the low-free-storage alarm threshold relative to what was actually provisioned (modules/rds)."
  type        = number
}

variable "elasticache_cluster_id" {
  type = string
}

# Scoped to the API service only, not all 5 -- it's the one user-facing,
# ALB-fronted service. Extend to the workers later if that turns out to
# matter; keeping this minimal on purpose (AWS_Deployment.md section 19:
# "do not create unnecessary observability infrastructure").
variable "ecs_cluster_name" {
  type = string
}

variable "ecs_api_service_name" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
