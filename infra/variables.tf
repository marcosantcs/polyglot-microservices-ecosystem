variable "aws_region" {
  default = "us-east-1"
}

variable "project_name" {
  default = "master-project"
}

variable "db_password" {
  description = "RDS PostgreSQL password"
  type        = string
  sensitive   = true
}

variable "db_username" {
  default = "postgres"
}

variable "db_name" {
  default = "ordersdb"
}

variable "order_service_image" {
  description = "ECR image URI for order-service"
  type        = string
}

variable "analytics_service_image" {
  description = "ECR image URI for analytics-service"
  type        = string
}
