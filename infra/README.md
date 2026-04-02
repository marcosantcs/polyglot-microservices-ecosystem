# Terraform — AWS Infrastructure

## Prerequisites
- Terraform >= 1.7
- AWS CLI configured (`aws configure`)
- S3 bucket for state: `microservices-terraform-state`

## Deploy

```bash
cd infra/
terraform init
terraform plan -var="db_username=postgres" -var="db_password=YOUR_PASS"
terraform apply -var="db_username=postgres" -var="db_password=YOUR_PASS"
```

## What this creates
- VPC with public/private subnets across 2 AZs
- NAT Gateway for private subnet egress
- ECS Cluster with Container Insights
- RDS PostgreSQL 16 (db.t3.micro) with 7-day backups
- Security Groups with least-privilege rules

## Destroy
```bash
terraform destroy -var="db_username=postgres" -var="db_password=YOUR_PASS"
```
