output "endpoint" {
  value = aws_db_instance.this.endpoint
}

output "instance_id" {
  description = "For CloudWatch AWS/RDS DBInstanceIdentifier dimension (modules/cloudwatch-alarms)."
  value       = aws_db_instance.this.id
}

output "database_name" {
  value = aws_db_instance.this.db_name
}

output "master_username" {
  value = aws_db_instance.this.username
}

output "database_url_secret_arn" {
  description = "Secrets Manager secret ARN holding the composed DATABASE_URL connection string -- reference this directly in the ECS task definition's `secrets` block."
  value       = aws_secretsmanager_secret.database_url.arn
}
