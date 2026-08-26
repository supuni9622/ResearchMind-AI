# Generic ECS/Fargate task definition + service, reused for the API
# (Phase 4), the four workers (Phase 5), and MCP (Phase 6) -- one backend
# image, role selected via `command`, matching docker-compose.yml and
# AWS_Deployment.md section 17.
#
# No ECS container-level health check is configured here. The API's
# liveness is checked by the ALB target group instead (modules/alb); the
# workers have no HTTP surface to check at all (see docs/deployment/
# 07-phase0-validation-findings.md section 5) and rely on ECS's default
# process-exit-code task replacement instead of an invented HTTP endpoint,
# per AWS_Deployment.md section 16.

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.name_prefix}-${var.service_name}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = "${var.name_prefix}-${var.service_name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  # Defaults to ARM64 (Graviton) -- found live, not anticipated: pushing
  # researchmind-backend from an Apple Silicon Mac without an explicit
  # `docker build --platform` produces an arm64-only image manifest, and
  # Fargate defaults to X86_64, so tasks failed with CannotPullContainerError
  # ("manifest does not contain descriptor matching platform linux/amd64").
  # Matching Fargate to the image's actual native architecture is both the
  # fix and a deliberate choice: Graviton is ~20% cheaper on Fargate for
  # the same vCPU/memory, and it deploys the exact image already validated
  # locally (torch CPU imports, the healthy Compose stack) rather than an
  # untested amd64 rebuild. Override to "X86_64" per-service if a given
  # image (e.g. research-intelligence-mcp, built in a separate repo/CI
  # this one doesn't control) isn't multi-arch.
  runtime_platform {
    cpu_architecture        = var.cpu_architecture
    operating_system_family = "LINUX"
  }

  container_definitions = jsonencode([
    {
      name      = var.service_name
      image     = var.image
      essential = true
      command   = var.command

      portMappings = var.container_port == null ? [] : [
        {
          containerPort = var.container_port
          protocol      = "tcp"
        }
      ]

      environment = [
        for name, value in var.environment : { name = name, value = value }
      ]

      secrets = [
        for name, arn in var.secrets : { name = name, valueFrom = arn }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.this.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = var.service_name
        }
      }
    }
  ])

  tags = var.tags
}

resource "aws_ecs_service" "this" {
  name            = "${var.name_prefix}-${var.service_name}"
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = true # public subnets, no NAT -- see the Phase 0 decision this module's variables.tf references
  }

  # Only matters when a load_balancer block exists (below) -- found live:
  # with no grace period, the ALB starts counting failed health checks the
  # instant a task registers as a target, which is often BEFORE the
  # container has even pulled the image (a ~900MB cold pull with no local
  # cache on the Fargate host took ~30s here) let alone started Uvicorn.
  # unhealthy_threshold(3) * interval(15s) in modules/alb can elapse before
  # the app is ever listening, so ECS kills a task that would have passed
  # moments later -- confirmed via CloudWatch logs showing real 200
  # responses to /api/v1/health/live logged seconds after the ALB had
  # already marked the target unhealthy. This doesn't affect the workers
  # (no target_group_arn, so no load_balancer block, so this is a no-op).
  health_check_grace_period_seconds = var.target_group_arn == null ? null : 120

  dynamic "load_balancer" {
    for_each = var.target_group_arn == null ? [] : [var.target_group_arn]
    content {
      target_group_arn = load_balancer.value
      container_name   = var.service_name
      container_port   = var.container_port
    }
  }

  dynamic "service_registries" {
    for_each = var.service_registry_arn == null ? [] : [var.service_registry_arn]
    content {
      registry_arn = service_registries.value
    }
  }

  tags = var.tags
}
