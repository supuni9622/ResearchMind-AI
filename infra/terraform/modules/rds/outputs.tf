output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "database_name" {
  value = aws_db_instance.this.db_name
}

output "master_username" {
  value = aws_db_instance.this.username
}

output "master_user_secret_arn" {
  description = "Secrets Manager secret ARN RDS created for the master password -- reference this in the ECS task definition's `secrets` block."
  value       = aws_db_instance.this.master_user_secret[0].secret_arn
}
