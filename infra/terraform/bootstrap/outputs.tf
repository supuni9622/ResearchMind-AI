output "state_bucket_name" {
  description = "S3 bucket name to use as `bucket` in every environment's backend \"s3\" block."
  value       = aws_s3_bucket.terraform_state.id
}

output "lock_table_name" {
  description = "DynamoDB table name to use as `dynamodb_table` in every environment's backend \"s3\" block."
  value       = aws_dynamodb_table.terraform_lock.name
}
