output "domain_name" {
  description = "The *.cloudfront.net HTTPS domain -- this is what NEXT_PUBLIC_API_URL should point at."
  value       = aws_cloudfront_distribution.api.domain_name
}
