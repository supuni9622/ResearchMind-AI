variable "name_prefix" {
  type = string
}

variable "alb_dns_name" {
  description = "The ALB's origin domain name -- CloudFront reaches it over plain HTTP; that leg never leaves AWS's network, only the CloudFront-facing side is HTTPS. See AWS_Deployment.md section 33."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
