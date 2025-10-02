# 🚀 RunPod Deployment Guide for XTTS Service

This guide walks you through deploying the CallWaiting.ai TTS service on RunPod using the provided template.

## 📋 Prerequisites

- RunPod account with credits
- Docker Hub or GitHub Container Registry account (for custom images)
- Access to the repository: `https://github.com/Odiabackend099/runpod-xtts.git`

## 🐳 Option 1: Use Pre-built Docker Image (Recommended)

### Step 1: Build and Push Docker Image

```bash
# Build the optimized RunPod image
docker build -f Dockerfile.runpod -t runpod-xtts:latest .

# Tag for Docker Hub (replace 'yourusername' with your Docker Hub username)
docker tag runpod-xtts:latest yourusername/runpod-xtts:latest

# Push to Docker Hub
docker push yourusername/runpod-xtts:latest
```

### Step 2: Update Template

Edit `runpod-xtts-template.yaml` and update the image line:
```yaml
image: docker.io/yourusername/runpod-xtts:latest
```

### Step 3: Deploy on RunPod

1. Go to [RunPod Dashboard](https://runpod.io/console/pods)
2. Click **"Deploy New Pod"**
3. Select **"From Template"**
4. Upload your `runpod-xtts-template.yaml` file
5. Click **"Deploy"**

## 🏗️ Option 2: Build on RunPod (Slower but No Registry Needed)

### Step 1: Deploy with Build

1. Go to RunPod Dashboard
2. Click **"Deploy New Pod"**
3. Select **"From Template"**
4. Upload `runpod-xtts-template.yaml`
5. **Modify the startCommand** to include build steps:

```yaml
startCommand: >
  bash -c "cd /workspace &&
           git clone https://github.com/Odiabackend099/runpod-xtts.git . &&
           docker build -f Dockerfile.runpod -t runpod-xtts:latest . &&
           uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"
```

## ⚙️ Template Configuration

The `runpod-xtts-template.yaml` includes:

- **GPU**: RTX 2000 Ada (adjustable based on your needs)
- **CPU**: Minimum 2 vCPUs
- **Memory**: 4GB RAM
- **Port**: 8000 (HTTP enabled, default)
- **Volume**: `/workspace` for persistence
- **Startup**: Optimized uvicorn command

## 🔧 Customization Options

### GPU Types
```yaml
gpu_type: RTX_2000_Ada    # Budget option
gpu_type: RTX_3000_Ada    # Mid-range
gpu_type: RTX_4000_Ada    # High-end
gpu_type: RTX_5000_Ada    # Premium
```

### Resource Scaling
```yaml
min_vcpus: 4              # More CPU cores
min_memory: 8Gi           # More RAM
```

### Multiple Workers
```yaml
startCommand: >
  bash -c "cd /workspace &&
           uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4"
```

## 🌐 Accessing Your Service

Once deployed, RunPod will provide:
- **External URL**: `https://your-pod-id-8000.proxy.runpod.net`
- **Direct Access**: Use this URL in your applications
- **Health Check**: `https://your-pod-id-8000.proxy.runpod.net/health`

## 📊 Monitoring

The service includes built-in monitoring:
- Health endpoint: `/health`
- Metrics endpoint: `/metrics` (if enabled)
- Logs available in RunPod console

## 💰 Cost Optimization

### Tips to Reduce Costs:
1. **Use RTX 2000 Ada** for development/testing
2. **Scale up to RTX 3000/4000** for production
3. **Stop pods** when not in use
4. **Use spot instances** for non-critical workloads

### Estimated Costs (as of 2024):
- RTX 2000 Ada: ~$0.20/hour
- RTX 3000 Ada: ~$0.40/hour
- RTX 4000 Ada: ~$0.60/hour

## 🔒 Security Considerations

1. **API Keys**: Store in environment variables
2. **HTTPS**: RunPod provides automatic HTTPS
3. **Rate Limiting**: Built into the service
4. **Authentication**: API key validation included

## 🚨 Troubleshooting

### Common Issues:

**Pod won't start:**
- Check Docker image exists and is accessible
- Verify startCommand syntax
- Check RunPod logs for errors

**Service not responding:**
- Verify port 8000 is exposed
- Check health endpoint: `/health`
- Review application logs

**GPU not detected:**
- Ensure `gpu: true` in template
- Check GPU type is available in your region
- Verify CUDA dependencies in Dockerfile

## 📞 Support

- **RunPod Support**: [RunPod Discord](https://discord.gg/runpod)
- **Service Issues**: Check GitHub issues
- **Documentation**: [RunPod Docs](https://docs.runpod.io/)

---

## 🎯 Quick Deploy Checklist

- [ ] Build and push Docker image (Option 1) OR prepare build command (Option 2)
- [ ] Update template with correct image name
- [ ] Upload template to RunPod
- [ ] Deploy pod
- [ ] Test health endpoint
- [ ] Configure your application with the RunPod URL
- [ ] Monitor costs and performance

**Ready to deploy! 🚀**
