# Kubernetes Deployment Guide

## Prerequisites
- kubectl configured
- minikube or any k8s cluster

## Deploy all services

```bash
# Create namespace and deploy all
kubectl apply -f namespace.yaml
kubectl apply -f postgres.yaml
kubectl apply -f rabbitmq.yaml
kubectl apply -f order-service.yaml
kubectl apply -f analytics-service.yaml

# Verify pods
kubectl get pods -n microservices

# Port-forward to test locally
kubectl port-forward svc/order-service 5000:5000 -n microservices
kubectl port-forward svc/rabbitmq 15672:15672 -n microservices
```

## Scale order-service manually
```bash
kubectl scale deployment order-service --replicas=5 -n microservices
```

## HPA (auto-scaling) is already configured
The order-service scales from 2 to 10 replicas at 70% CPU.
