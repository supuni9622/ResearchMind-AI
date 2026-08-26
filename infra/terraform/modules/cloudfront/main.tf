# HTTPS front door for the ALB (AWS_Deployment.md section 33). No custom
# domain, so this relies on CloudFront's own *.cloudfront.net domain with
# an AWS-provided certificate -- automatic, no ACM validation needed.
# Resolves the Phase 7 mixed-content blocker: the Amplify frontend is
# HTTPS, and browsers block an HTTPS page calling a plain-HTTP API.
#
# Cost is effectively $0 at this project's traffic level -- within
# CloudFront's free tier (1TB/month data transfer, 10M requests/month).
#
# Lives in the ecs-demo state deliberately, not a separate one: its whole
# purpose is fronting THIS cycle's ALB, which gets a new DNS name every
# time ecs-demo is destroyed and reapplied. There's nothing for it to
# front once the ALB is gone, so it should be destroyed and recreated
# alongside it, not decoupled like Amplify (see environments/frontend).
#
# Caching is disabled (AWS managed "CachingDisabled" policy) -- this
# fronts a dynamic JSON API, not static assets; nothing here should be
# cached at the edge by default.

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

resource "aws_cloudfront_distribution" "api" {
  enabled = true
  comment = "${var.name_prefix} API (HTTPS front door for the ALB)"

  origin {
    domain_name = var.alb_dns_name
    origin_id   = "alb"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only" # the ALB itself stays HTTP-only, see modules/alb
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods  = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "alb"

    viewer_protocol_policy   = "redirect-to-https"
    cache_policy_id          = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = var.tags
}
