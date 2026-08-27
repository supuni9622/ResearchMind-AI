variable "name_prefix" {
  description = "Prefix applied to every IAM role/policy name created by this module."
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the existing S3 documents bucket (S3 already exists per AWS_Deployment.md section 12 -- this module references it, it does not create it)."
  type        = string
}

variable "sqs_queue_arns" {
  description = "ARNs of the existing SQS queue(s) the app needs (main + DLQ). SQS already exists per AWS_Deployment.md section 11 -- referenced, not created here."
  type        = list(string)
}

variable "secrets_manager_secret_arns" {
  description = "ARNs (or ARN prefixes with a trailing *) of the Secrets Manager secrets the ECS task execution role may read to inject as container secrets."
  type        = list(string)
}

variable "tags" {
  description = "Common tags applied to every resource."
  type        = map(string)
  default     = {}
}
