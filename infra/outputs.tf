output "alb_dns_name" {
  description = "URL pública do Load Balancer"
  value       = aws_lb.main.dns_name
}

output "rds_endpoint" {
  description = "Endpoint do banco PostgreSQL"
  value       = aws_db_instance.postgres.endpoint
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecr_order_service_url" {
  value = aws_ecr_repository.order_service.repository_url
}

output "ecr_analytics_service_url" {
  value = aws_ecr_repository.analytics_service.repository_url
}
