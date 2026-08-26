variable "path_prefix" {
  description = "Secrets Manager name prefix -- must match the prefix the IAM execution role's secretsmanager:GetSecretValue policy is scoped to (modules/iam's secrets_manager_secret_arns)."
  type        = string
}

variable "secret_names" {
  description = "Short secret names, created under path_prefix as empty containers. Populate actual values out-of-band (console or `aws secretsmanager put-secret-value`) -- never through Terraform, so third-party API keys never end up in tfstate."
  type        = list(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}
