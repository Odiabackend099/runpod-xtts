# 🚀 RunPod Deployment Guide (XTTS)

## Deployment
1. Go to RunPod Dashboard → Deploy New Pod  
2. Select **From GitHub Repo**  
3. Paste: `https://github.com/Odiabackend099/runpod-xtts.git`  
4. RunPod reads `runpod.yaml` and configures everything.

## Test
```bash
curl https://<your-pod-id>-8888.proxy.runpod.net/health
```

## Example Synthesis

```bash
curl -X POST "https://<your-pod-id>-8888.proxy.runpod.net/synthesize" \
-H "Authorization: Bearer cw_demo_12345" \
-F "text=Hello from Nigeria!" \
-F "voice_id=naija_female" \
--output hello.mp3
```

## Available Voices

- **default**: en-US-AriaNeural (neutral)
- **naija_female**: en-US-JennyNeural (female)
- **naija_male**: en-US-GuyNeural (male)
- **professional**: en-US-DavisNeural (male)
- **friendly**: en-US-EmmaNeural (female)
- **calm**: en-US-MichelleNeural (female)
- **energetic**: en-US-BrandonNeural (male)

## API Endpoints

- `GET /health` - Health check
- `GET /voices` - List available voices
- `POST /synthesize` - Synthesize text to speech
- `GET /tenant/stats` - Get tenant statistics

## API Keys

- **Demo Key**: `cw_demo_12345` (tenant: callwaiting_demo)
- **Test Key**: `test_key_67890` (tenant: test_tenant)

## Configuration

The service runs on port 8888 and includes:
- GPU support (RTX 2000 Ada)
- 2 vCPUs minimum
- 4GB RAM
- Persistent `/workspace` volume
- Automatic HTTPS proxy

## Cost

Approximately $0.20/hour with RTX 2000 Ada GPU.

## Support

For issues, check the RunPod console logs or GitHub repository.