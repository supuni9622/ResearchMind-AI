output "app_id" {
  value = aws_amplify_app.web.id
}

output "predicted_base_url" {
  description = "Amplify's default domain pattern for branch \"main\", computed from the app_id this apply just created -- feed this back in as the base_url variable and apply again (see variables.tf). Only real once the GitHub repo/branch is actually connected via the Console (manual step, see AWS_Deployment.md section 35)."
  value       = "https://main.${aws_amplify_app.web.id}.amplifyapp.com"
}

output "cognito_callback_url_to_add" {
  description = "Once base_url is set (second apply), paste into `aws cognito-idp update-user-pool-client --callback-urls` alongside any existing URLs -- this ADDS to the list, it does not replace it. Empty until base_url is set."
  value       = var.base_url == "" ? null : "${var.base_url}/auth/callback"
}

output "cognito_logout_url_to_add" {
  value = var.base_url == "" ? null : var.base_url
}
