# CallWaiting.ai TTS Service - Deployment Guide

This guide covers deploying the TTS microservice in various environments, from local development to production cloud deployments.

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- Redis (for rate limiting and caching)
- PostgreSQL (for production voice storage)
- GPU support (optional, for better performance)

## 🚀 Quick Start

### Local Development

1. **Clone and setup:**
```bash
cd /Users/odiadev/Desktop/tts/tts-service
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Start Redis:**
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

3. **Run the service:**
```bash
python -m src.server
```

4. **Test the API:**
```bash
curl http://localhost:8000/v1/health
```

### Docker Deployment

1. **Build and run:**
```bash
docker-compose up --build
```

2. **Access the service:**
- API: http://localhost:8000
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/v1/health

## 🐳 Docker Configuration

### Multi-stage Dockerfile

The Dockerfile uses a multi-stage build for optimal image size:

```dockerfile
# Builder stage - installs dependencies
FROM python:3.9-slim as builder
# ... build dependencies

# Production stage - minimal runtime
FROM python:3.9-slim
# ... runtime dependencies
```

### Docker Compose Services

- **tts-service**: Main TTS application
- **redis**: Rate limiting and caching
- **nginx**: Load balancer and SSL termination

### Environment Variables

Create a `.env` file:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4

# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/tts_service

# Redis
REDIS_URL=redis://redis:6379/0

# TTS Configuration
TTS_AGREE_TO_CPML=1
TTS_MODEL_PATH=tts_models/multilingual/multi-dataset/xtts_v2

# Security
JWT_SECRET_KEY=your-secret-key-here
API_KEY_SALT=your-salt-here

# Monitoring
LOG_LEVEL=INFO
METRICS_ENABLED=true
```

## ☁️ Cloud Deployment

### AWS ECS

1. **Create ECS cluster:**
```bash
aws ecs create-cluster --cluster-name tts-cluster
```

2. **Create task definition:**
```json
{
  "family": "tts-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "4096",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "tts-service",
      "image": "your-account.dkr.ecr.region.amazonaws.com/tts-service:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "HOST", "value": "0.0.0.0"},
        {"name": "PORT", "value": "8000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/tts-service",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

3. **Create service:**
```bash
aws ecs create-service \
  --cluster tts-cluster \
  --service-name tts-service \
  --task-definition tts-service:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

### Google Cloud Run

1. **Build and push image:**
```bash
gcloud builds submit --tag gcr.io/PROJECT-ID/tts-service
```

2. **Deploy service:**
```bash
gcloud run deploy tts-service \
  --image gcr.io/PROJECT-ID/tts-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --concurrency 50 \
  --max-instances 10
```

3. **Set environment variables:**
```bash
gcloud run services update tts-service \
  --set-env-vars="HOST=0.0.0.0,PORT=8080,REDIS_URL=redis://redis:6379"
```

### Azure Container Instances

1. **Create resource group:**
```bash
az group create --name tts-rg --location eastus
```

2. **Deploy container:**
```bash
az container create \
  --resource-group tts-rg \
  --name tts-service \
  --image your-registry.azurecr.io/tts-service:latest \
  --cpu 2 \
  --memory 4 \
  --ports 8000 \
  --environment-variables \
    HOST=0.0.0.0 \
    PORT=8000 \
    REDIS_URL=redis://redis:6379
```

## ☸️ Kubernetes Deployment

### Helm Chart

1. **Install Helm chart:**
```bash
helm install tts-service ./helm/tts-service \
  --set image.repository=your-registry/tts-service \
  --set image.tag=latest \
  --set replicaCount=3 \
  --set resources.requests.memory=2Gi \
  --set resources.requests.cpu=1000m \
  --set resources.limits.memory=4Gi \
  --set resources.limits.cpu=2000m
```

2. **Scale deployment:**
```bash
kubectl scale deployment tts-service --replicas=5
```

### Kubernetes Manifests

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tts-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tts-service
  template:
    metadata:
      labels:
        app: tts-service
    spec:
      containers:
      - name: tts-service
        image: your-registry/tts-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8000"
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "2Gi"
            cpu: "1000m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /v1/health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: tts-service
spec:
  selector:
    app: tts-service
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 🔧 Production Configuration

### Performance Optimization

1. **GPU Support:**
```bash
# For NVIDIA GPU
docker run --gpus all -e CUDA_VISIBLE_DEVICES=0 tts-service
```

2. **Memory Optimization:**
```bash
# Increase shared memory for model loading
docker run --shm-size=2g tts-service
```

3. **CPU Optimization:**
```bash
# Pin to specific CPUs
docker run --cpuset-cpus="0-3" tts-service
```

### Security Configuration

1. **API Key Management:**
```python
# Generate secure API keys
import secrets
api_key = f"sk_prod_{secrets.token_urlsafe(32)}"
```

2. **Rate Limiting:**
```python
# Configure per-tenant limits
RATE_LIMITS = {
    "premium": {"requests_per_minute": 5000, "requests_per_hour": 50000},
    "standard": {"requests_per_minute": 1000, "requests_per_hour": 10000},
    "basic": {"requests_per_minute": 100, "requests_per_hour": 1000}
}
```

3. **SSL/TLS:**
```nginx
server {
    listen 443 ssl http2;
    server_name tts.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/tts.crt;
    ssl_certificate_key /etc/ssl/private/tts.key;
    
    location / {
        proxy_pass http://tts-service:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Monitoring and Logging

1. **Prometheus Metrics:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'tts-service'
    static_configs:
      - targets: ['tts-service:8000']
    metrics_path: '/v1/metrics'
    scrape_interval: 15s
```

2. **Grafana Dashboard:**
```json
{
  "dashboard": {
    "title": "TTS Service Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(tts_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      }
    ]
  }
}
```

3. **Log Aggregation:**
```yaml
# docker-compose.yml
services:
  tts-service:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
  
  elasticsearch:
    image: elasticsearch:7.14.0
    environment:
      - discovery.type=single-node
  
  kibana:
    image: kibana:7.14.0
    ports:
      - "5601:5601"
```

## 🔍 Health Checks and Monitoring

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/v1/health

# Detailed metrics (admin only)
curl -H "Authorization: Bearer sk_admin_xxx" \
  http://localhost:8000/v1/metrics
```

### Key Metrics to Monitor

- **Latency**: Time to first audio chunk (< 200ms)
- **Throughput**: Requests per second
- **Error Rate**: Should be < 0.1%
- **Memory Usage**: Should be < 80%
- **CPU Usage**: Should be < 70%
- **Active Connections**: Monitor concurrent streams

### Alerting Rules

```yaml
# alertmanager.yml
groups:
  - name: tts-service
    rules:
      - alert: HighErrorRate
        expr: rate(tts_errors_total[5m]) > 0.01
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "TTS service error rate is high"
      
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(tts_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "TTS service latency is high"
```

## 🚨 Troubleshooting

### Common Issues

1. **Model Loading Failures:**
```bash
# Check model files
ls -la /app/models/
# Verify TTS_AGREE_TO_CPML=1
echo $TTS_AGREE_TO_CPML
```

2. **Memory Issues:**
```bash
# Monitor memory usage
docker stats tts-service
# Increase memory limits
docker run --memory=8g tts-service
```

3. **Redis Connection Issues:**
```bash
# Test Redis connection
redis-cli -h redis ping
# Check Redis logs
docker logs redis
```

4. **Audio Quality Issues:**
```bash
# Check sample rate
ffprobe output.wav
# Verify voice configuration
curl -H "Authorization: Bearer sk_test_xxx" \
  http://localhost:8000/v1/voices
```

### Performance Tuning

1. **Model Preloading:**
```python
# Preload models on startup
await tts_model.initialize()
await tts_model.preload_voice("naija_female")
```

2. **Connection Pooling:**
```python
# Configure database connection pool
DATABASE_URL = "postgresql://user:pass@host:5432/db?pool_size=20&max_overflow=30"
```

3. **Caching Strategy:**
```python
# Cache frequently used audio
@lru_cache(maxsize=1000)
def get_cached_audio(text_hash: str) -> bytes:
    return synthesize_audio(text_hash)
```

## 📊 Load Testing

### Artillery Load Test

```yaml
# load-test.yml
config:
  target: 'http://localhost:8000'
  phases:
    - duration: 60
      arrivalRate: 10
    - duration: 120
      arrivalRate: 50
    - duration: 60
      arrivalRate: 100

scenarios:
  - name: "TTS Synthesis"
    weight: 100
    flow:
      - post:
          url: "/v1/synthesize"
          headers:
            Authorization: "Bearer sk_test_1234567890abcdef"
          form:
            text: "Hello from load test"
            voice_id: "naija_female"
            streaming: "true"
```

### Run Load Test

```bash
# Install Artillery
npm install -g artillery

# Run load test
artillery run load-test.yml

# Generate report
artillery run load-test.yml --output report.json
artillery report report.json
```

## 🔄 Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
pg_dump -h postgres -U tts_user tts_service > backup.sql

# Restore from backup
psql -h postgres -U tts_user tts_service < backup.sql
```

### Voice Storage Backup

```bash
# Backup voice files
tar -czf voice_storage_backup.tar.gz voice_storage/

# Restore voice files
tar -xzf voice_storage_backup.tar.gz
```

### Configuration Backup

```bash
# Backup configuration
kubectl get configmap tts-config -o yaml > config-backup.yaml

# Restore configuration
kubectl apply -f config-backup.yaml
```

## 📈 Scaling Strategies

### Horizontal Scaling

1. **Load Balancer Configuration:**
```nginx
upstream tts_backend {
    least_conn;
    server tts-service-1:8000;
    server tts-service-2:8000;
    server tts-service-3:8000;
}
```

2. **Auto-scaling:**
```yaml
# HPA configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tts-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tts-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Vertical Scaling

1. **Resource Limits:**
```yaml
resources:
  requests:
    memory: "4Gi"
    cpu: "2000m"
  limits:
    memory: "8Gi"
    cpu: "4000m"
```

2. **GPU Scaling:**
```yaml
# GPU-enabled deployment
resources:
  limits:
    nvidia.com/gpu: 1
```

## 🎯 Best Practices

1. **Security:**
   - Use HTTPS in production
   - Rotate API keys regularly
   - Implement proper authentication
   - Monitor for suspicious activity

2. **Performance:**
   - Use connection pooling
   - Implement caching strategies
   - Monitor resource usage
   - Optimize model loading

3. **Reliability:**
   - Implement health checks
   - Use circuit breakers
   - Set up monitoring and alerting
   - Plan for disaster recovery

4. **Maintenance:**
   - Regular security updates
   - Monitor logs and metrics
   - Plan for capacity growth
   - Test disaster recovery procedures

---

**Need help?** Check the troubleshooting section or create an issue in the repository.
