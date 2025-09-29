# RunPod Pod Deployment Guide for CallWaiting.ai TTS Service

## Overview

This guide shows you how to deploy your CallWaiting.ai TTS service on your existing RunPod pod with RTX 2000 Ada GPU.

## Your Pod Configuration

- **GPU**: RTX 2000 Ada x1
- **vCPU**: 6 cores
- **Memory**: 31 GB
- **Container Disk**: 30 GB
- **Volume Storage**: 50 GB at `/workspace`
- **Template**: runpod-torch-v280
- **Cost**: $0.0139/hr (when running)

## Deployment Options

### Option 1: Quick Deploy (Recommended)

Use the automated deployment script:

```bash
./deploy_to_runpod.sh
```

This script will:
1. Build the Docker image
2. Create RunPod template configuration
3. Provide step-by-step deployment instructions

### Option 2: Manual Deployment

#### Step 1: Build Docker Image

```bash
# Build the optimized image for your pod
docker build -f Dockerfile.runpod.pod -t callwaiting-tts-service .
```

#### Step 2: Create RunPod Template

1. Go to RunPod Dashboard → Templates
2. Click "New Template"
3. Configure:
   - **Name**: `callwaiting-tts-service`
   - **Container Image**: `callwaiting-tts-service:latest` (or your registry)
   - **Container Disk**: 30 GB
   - **Volume**: 50 GB at `/workspace`
   - **Ports**: `8000/http`
   - **Environment Variables**:
     ```
     PYTHONPATH=/workspace
     PYTHONUNBUFFERED=1
     HOST=0.0.0.0
     PORT=8000
     ```
   - **Start Jupyter**: No
   - **Start SSH**: Yes (for debugging)

#### Step 3: Deploy to Your Pod

1. Go to RunPod Dashboard → Pods
2. Find your `far_azure_tern` pod
3. Click "Deploy" or "Start"
4. Select the `callwaiting-tts-service` template
5. Deploy

#### Step 4: Access Your Service

Once deployed, your TTS service will be available at:
- **HTTP Endpoint**: `http://YOUR_POD_IP:8000`
- **Health Check**: `http://YOUR_POD_IP:8000/v1/health`
- **API Documentation**: `http://YOUR_POD_IP:8000/docs`

## Testing Your Deployment

### Using the Pod Client

```bash
# Set your pod IP
export RUNPOD_POD_IP="YOUR_POD_IP"

# Test the service
python3 runpod_pod_client.py
```

### Manual Testing

```bash
# Health check
curl -H "Authorization: Bearer cw_demo_12345" \
     http://YOUR_POD_IP:8000/v1/health

# List voices
curl -H "Authorization: Bearer cw_demo_12345" \
     http://YOUR_POD_IP:8000/v1/voices

# Synthesize text
curl -X POST \
     -H "Authorization: Bearer cw_demo_12345" \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello, this is a test", "voice_id": "default"}' \
     http://YOUR_POD_IP:8000/v1/synthesize \
     --output test_audio.mp3
```

## API Endpoints

### Health Check
```
GET /v1/health
```

### List Voices
```
GET /v1/voices
```

### Synthesize Text
```
POST /v1/synthesize
Content-Type: application/json
Authorization: Bearer cw_demo_12345

{
  "text": "Hello, this is a test",
  "voice_id": "default",
  "language": "en"
}
```

### Streaming Synthesis
```
POST /v1/synthesize/streaming
Content-Type: application/json
Authorization: Bearer cw_demo_12345

{
  "text": "Hello, this is a streaming test",
  "voice_id": "professional",
  "language": "en"
}
```

### Generate Demo Audio
```
POST /v1/generate-demo-audio
Authorization: Bearer cw_demo_12345
```

### Tenant Statistics
```
GET /v1/tenant/stats
Authorization: Bearer cw_demo_12345
```

## Available Voices

| Voice ID | Description | Edge TTS Voice |
|----------|-------------|----------------|
| `default` | Default voice | en-US-AriaNeural |
| `naija_female` | Nigerian female | en-US-JennyNeural |
| `naija_male` | Nigerian male | en-US-GuyNeural |
| `professional` | Professional tone | en-US-DavisNeural |
| `friendly` | Friendly tone | en-US-EmmaNeural |
| `calm` | Calm tone | en-US-MichelleNeural |
| `energetic` | Energetic tone | en-US-BrianNeural |

## Performance Expectations

With your RTX 2000 Ada GPU:
- **Response Time**: 2-5 seconds for typical text
- **Concurrent Requests**: 5-10 simultaneous
- **Audio Quality**: High-quality MP3 (48 kbps, 24 kHz)
- **Memory Usage**: ~2-4 GB for TTS operations
- **GPU Utilization**: Moderate (Edge TTS is CPU-optimized)

## Cost Management

### Current Costs
- **Pod**: $0.0139/hr when running
- **Volume Storage**: $0.0139/hr (50 GB)
- **Total**: ~$0.28/day when running

### Cost Optimization Tips
1. **Stop Pod When Not in Use**: Use RunPod's start/stop functionality
2. **Monitor Usage**: Set up billing alerts
3. **Optimize Text Length**: Shorter texts = faster processing
4. **Batch Requests**: Process multiple texts in one session

## Monitoring and Debugging

### Accessing Your Pod
1. **SSH Access**: Enable SSH in template settings
2. **Jupyter**: Optional for development
3. **Logs**: View in RunPod dashboard

### Common Issues

1. **Port Not Accessible**
   - Check firewall settings
   - Verify port 8000 is exposed
   - Ensure service is running

2. **Out of Memory**
   - Monitor memory usage
   - Restart pod if needed
   - Optimize text length

3. **Slow Response**
   - Check GPU utilization
   - Monitor network latency
   - Consider text length optimization

### Health Monitoring

```bash
# Check service status
curl http://YOUR_POD_IP:8000/v1/health

# Monitor logs (via SSH)
tail -f /workspace/logs/tts_service.log
```

## Integration Examples

### Python Client
```python
from runpod_pod_client import RunPodPodTTSClient

client = RunPodPodTTSClient("YOUR_POD_IP")
audio_data = client.synthesize("Hello, world!")
```

### JavaScript/Node.js
```javascript
const response = await fetch('http://YOUR_POD_IP:8000/v1/synthesize', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer cw_demo_12345',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: 'Hello, world!',
    voice_id: 'default'
  })
});

const audioData = await response.arrayBuffer();
```

### cURL
```bash
curl -X POST \
  -H "Authorization: Bearer cw_demo_12345" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, world!", "voice_id": "default"}' \
  http://YOUR_POD_IP:8000/v1/synthesize \
  --output audio.mp3
```

## Security Considerations

### API Key Management
- Use strong API keys in production
- Rotate keys regularly
- Monitor API usage

### Network Security
- Consider VPN access for production
- Use HTTPS in production (requires SSL setup)
- Implement rate limiting

### Data Privacy
- Audio data is processed in memory
- No persistent storage of audio files
- Consider data retention policies

## Scaling and Production

### For Production Use
1. **Load Balancer**: Use multiple pods behind a load balancer
2. **SSL/TLS**: Set up HTTPS for secure communication
3. **Monitoring**: Implement comprehensive monitoring
4. **Backup**: Regular backup of configurations
5. **Updates**: Plan for service updates and maintenance

### Auto-scaling
- RunPod doesn't support auto-scaling for pods
- Consider serverless deployment for auto-scaling
- Use multiple pods for high availability

## Support and Troubleshooting

### RunPod Resources
- **Documentation**: [docs.runpod.io](https://docs.runpod.io)
- **Community**: [Discord](https://discord.gg/runpod)
- **Support**: RunPod support tickets

### Common Commands
```bash
# Check pod status
runpod pod list

# Start/stop pod
runpod pod start POD_ID
runpod pod stop POD_ID

# View logs
runpod pod logs POD_ID
```

## Next Steps

1. **Deploy**: Follow the deployment steps above
2. **Test**: Use the provided client to test functionality
3. **Integrate**: Integrate with your CallWaiting.ai application
4. **Monitor**: Set up monitoring and alerts
5. **Optimize**: Monitor performance and optimize as needed

Your TTS service is now ready for production use on RunPod! 🚀
