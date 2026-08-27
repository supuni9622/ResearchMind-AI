output "dns_name" {
  value = aws_lb.this.dns_name
}

output "target_group_arn" {
  value = aws_lb_target_group.api.arn
}

output "arn_suffix" {
  description = "For CloudWatch AWS/ApplicationELB LoadBalancer dimension (modules/cloudwatch-alarms)."
  value       = aws_lb.this.arn_suffix
}

output "target_group_arn_suffix" {
  description = "For CloudWatch AWS/ApplicationELB TargetGroup dimension (modules/cloudwatch-alarms)."
  value       = aws_lb_target_group.api.arn_suffix
}
