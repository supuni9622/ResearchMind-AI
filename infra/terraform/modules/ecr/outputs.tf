output "repository_urls" {
  description = "Map of repository name -> repository URL, for `docker push`/task-definition image references."
  value       = { for name, repo in aws_ecr_repository.this : name => repo.repository_url }
}
