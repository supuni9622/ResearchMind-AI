variable "repository_names" {
  description = "ECR repository names to create."
  type        = list(string)
}

variable "max_image_count" {
  description = "Number of tagged images to retain per repository before older ones expire -- keeps ECR storage cost bounded without babysitting it manually."
  type        = number
  default     = 10
}

variable "tags" {
  description = "Common tags applied to every repository."
  type        = map(string)
  default     = {}
}
