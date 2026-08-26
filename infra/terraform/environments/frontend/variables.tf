variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "app_name" {
  type    = string
  default = "researchmind-web"
}

# No default -- this is the ecs-demo environment's `api_https_url` output
# (the CloudFront domain fronting that cycle's ALB). Update and reapply
# whenever ecs-demo is destroyed/recreated, since CloudFront gets a new
# *.cloudfront.net domain each time. See AWS_Deployment.md section 32/33.
variable "api_url" {
  description = "HTTPS API URL -- ecs-demo's `api_https_url` output (CloudFront, not the direct ALB)."
  type        = string
}

# Empty on the first apply (this app's own ID isn't known yet -- see
# main.tf's comment on why it can't be derived automatically). After the
# first apply, set this to "https://main.<app_id output>.amplifyapp.com"
# and apply again.
variable "base_url" {
  description = "This app's own public URL. Leave \"\" on the first apply; fill in from the app_id output afterward."
  type        = string
  default     = ""
}

# Cognito already exists (AWS_Deployment.md section 13) -- same real,
# non-sensitive values as environments/ecs-demo's defaults. Only these two
# are needed client-side (unlike the backend, the frontend never needs
# the user pool ID itself -- confirmed by grepping apps/web/src, which
# has no NEXT_PUBLIC_COGNITO_USER_POOL_ID reference at all).
variable "cognito_app_client_id" {
  type    = string
  default = "1r4at7v1s9nr9jqots6gl15ht"
}

variable "cognito_domain" {
  type    = string
  default = "https://us-east-19chs0pt6p.auth.us-east-1.amazoncognito.com"
}
