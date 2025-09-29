# RunPod Deployment Guide for CallWaiting.ai TTS Service

## Overview

This guide shows you how to deploy your CallWaiting.ai TTS service on RunPod's serverless infrastructure for scalable, GPU-accelerated text-to-speech generation.

## Why RunPod?

- **Serverless Architecture**: Pay only for compute time used
- **GPU Acceleration**: Access to powerful GPUs for faster processing
- **Auto-scaling**: Automatically handles traffic spikes
- **Global Edge**: Deploy closer to your users
- **Cost-effective**: No idle server costs

## Prerequisites

1. **RunPod Account**: Sign up at [runpod.io](https://runpod.io)
2. **API Key**: Generate an API key in your RunPod dashboard
3. **Docker**: For local testing (optional)

## Deployment Options

### Option 1: RunPod Serverless (Recommended)

**Best for**: Production workloads, auto-scaling, cost optimization

#### Step 1: Prepare Your Code

The `runpod_handler.py` file contains the serverless handler:

```python
# Key features:
- Edge TTS integration
- Base64 audio encoding
- Error handling
- Logging
- Input validation
```

#### Step 2: Create RunPod Template

1. Go to RunPod Dashboard → Templates
2. Click "New Template"
3. Configure:
   - **Name**: `callwaiting-tts-service`
   - **Container Image**: Your Docker image URL
   - **Container Start Command**: `python runpod_handler.py`
   - **Environment Variables**:
     ```
     PYTHONPATH=/app
     PYTHONUNBUFFERED=1
     ```

#### Step 3: Deploy Serverless Endpoint

1. Go to RunPod Dashboard → Serverless
2. Click "New Endpoint"
3. Configure:
   - **Template**: Select your template
   - **GPU Type**: `RTX 4090` or `A100` (recommended)
   - **Min Workers**: `0` (for cost optimization)
   - **Max Workers**: `10` (adjust based on expected load)
   - **Idle Timeout**: `30 seconds`

#### Step 4: Test Your Endpoint

```bash
# Set your endpoint ID
export RUNPOD_ENDPOINT_ID="your-endpoint-id"
export RUNPOD_API_KEY="your-api-key"

# Test the client
python runpod_client.py
```

### Option 2: RunPod Pods (Dedicated)

**Best for**: Development, testing, consistent workloads

#### Step 1: Create Pod Template

1. Go to RunPod Dashboard → Templates
2. Create new template with:
   - **Container Image**: Your Docker image
   - **Expose HTTP Ports**: `8000`
   - **Container Start Command**: `python real_tts_server.py`

#### Step 2: Deploy Pod

1. Go to RunPod Dashboard → Pods
2. Deploy new pod:
   - **GPU Type**: `RTX 4090` or `A100`
   - **Template**: Your template
   - **Region**: Choose closest to your users

## Configuration Files

### Dockerfile.runpod
```dockerfile
# Optimized for RunPod deployment
FROM python:3.9-slim
# ... (see file for complete configuration)
```

### requirements.runpod.txt
```
# Minimal dependencies for RunPod
runpod>=1.0.0
edge-tts>=6.1.0
# ... (see file for complete list)
```

### runpod_handler.py
```python
# Serverless handler function
def handler(event):
    # Process TTS request
    # Return base64 encoded audio
```

## API Usage

### Synchronous Request
```python
from runpod_client import RunPodTTSClient

client = RunPodTTSClient("your-endpoint-id", "your-api-key")

audio_data = client.synthesize(
    text="Hello, this is a test",
    voice_id="default",
    language="en"
)

if audio_data:
    with open("output.mp3", "wb") as f:
        f.write(audio_data)
```

### Asynchronous Request
```python
# Start async job
job_id = client.synthesize_async(
    text="Long text here...",
    voice_id="professional"
)

# Wait for completion
audio_data = client.wait_for_completion(job_id)
```

### cURL Example
```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "text": "Hello, this is a test",
      "voice_id": "default",
      "language": "en"
    }
  }'
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

## Cost Optimization

### Serverless Configuration
- **Min Workers**: 0 (no idle costs)
- **Max Workers**: 10 (handle traffic spikes)
- **Idle Timeout**: 30 seconds (quick shutdown)
- **GPU Type**: RTX 4090 (good performance/cost ratio)

### Usage Monitoring
```python
# Monitor your usage in RunPod dashboard
# Set up billing alerts
# Use async requests for batch processing
```

## Performance Considerations

### GPU Selection
- **RTX 4090**: Best performance/cost for TTS
- **A100**: Highest performance, higher cost
- **RTX 3080**: Budget option, good performance

### Optimization Tips
1. **Batch Processing**: Use async requests for multiple texts
2. **Voice Caching**: Cache frequently used voices
3. **Text Length**: Limit text to 5000 characters
4. **Connection Pooling**: Reuse HTTP connections

## Monitoring and Logging

### RunPod Dashboard
- Monitor request volume
- Track response times
- View error rates
- Monitor costs

### Application Logs
```python
# Logs are automatically captured
# View in RunPod dashboard → Logs
# Set up alerts for errors
```

## Security

### API Key Management
```bash
# Store API keys securely
export RUNPOD_API_KEY="your-secure-api-key"

# Use environment variables
# Never commit API keys to code
```

### Input Validation
```python
# Handler validates all inputs
# Text length limits
# Voice ID validation
# Error handling
```

## Troubleshooting

### Common Issues

1. **Cold Start Delays**
   - Solution: Keep min workers > 0 for critical workloads
   - Monitor: Set up alerts for response times

2. **Memory Issues**
   - Solution: Use larger GPU instances
   - Monitor: Check memory usage in logs

3. **Timeout Errors**
   - Solution: Increase timeout settings
   - Monitor: Optimize text length

### Debug Mode
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Migration from Local Service

### Step 1: Test Locally
```bash
# Test RunPod handler locally
python runpod_handler.py
```

### Step 2: Deploy to RunPod
```bash
# Build and push Docker image
docker build -f Dockerfile.runpod -t your-registry/tts-service .
docker push your-registry/tts-service
```

### Step 3: Update Client Code
```python
# Replace local client with RunPod client
from runpod_client import RunPodTTSClient
# Update endpoint configuration
```

## Best Practices

1. **Error Handling**: Always handle API errors gracefully
2. **Retry Logic**: Implement exponential backoff
3. **Monitoring**: Set up alerts for failures
4. **Cost Control**: Monitor usage and set limits
5. **Security**: Use secure API key management
6. **Testing**: Test with various text lengths and voices

## Support

- **RunPod Documentation**: [docs.runpod.io](https://docs.runpod.io)
- **RunPod Community**: [Discord](https://discord.gg/runpod)
- **GitHub Issues**: Report bugs and feature requests

## Example Deployment Script

```bash
#!/bin/bash
# deploy_to_runpod.sh

# Set variables
ENDPOINT_ID="your-endpoint-id"
API_KEY="your-api-key"

# Test deployment
echo "Testing RunPod TTS service..."
python runpod_client.py

# Verify deployment
curl -X POST "https://api.runpod.ai/v2/$ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"text": "Deployment test", "voice_id": "default"}}'

echo "Deployment complete!"
```

This guide provides everything you need to deploy your TTS service on RunPod's scalable infrastructure.
