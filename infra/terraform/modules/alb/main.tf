# Application Load Balancer for the ECS API (AWS_Deployment.md section 15).
#
# HTTP only (port 80) for now -- no custom domain is configured for this
# project, and ACM certificates require domain ownership/validation, so
# there's no way to put a real cert on the ALB's own *.elb.amazonaws.com
# DNS name. This is a known, deliberate limitation, not an oversight: it's
# enough to get the API reachable and testable (curl/Postman, Phase 10
# testing) now. Phase 7 (Amplify frontend) will need this revisited before
# the browser-based frontend can call it -- an HTTPS page fetching an HTTP
# API gets blocked as mixed content by every modern browser. Resolving
# that needs either a custom domain (Route 53 + ACM) or another approach;
# don't invent a domain here without one actually being available.

resource "aws_lb" "this" {
  name               = "${var.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = var.public_subnet_ids
  security_groups    = [var.security_group_id]

  tags = var.tags
}

resource "aws_lb_target_group" "api" {
  name        = "${var.name_prefix}-api"
  port        = var.api_container_port
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip" # required for awsvpc-mode Fargate tasks

  health_check {
    path                = var.health_check_path
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  tags = var.tags
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}
