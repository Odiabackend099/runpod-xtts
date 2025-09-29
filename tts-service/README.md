# CallWaiting.ai TTS Service

High-performance Text-to-Speech microservice using **Coqui XTTS** for CallWaiting.ai. Provides streaming audio synthesis, multi-tenant voice management, and voice cloning capabilities.

## 🚀 Features

- **High-Quality Neural Voices**: Powered by Coqui XTTS v2
- **Streaming Audio**: Real-time audio generation with <200ms latency
- **Multi-Tenant Support**: Isolated voice profiles per tenant
- **Voice Cloning**: Upload reference audio for custom voices
- **SSML Support**: Enhanced text markup for prosody and pauses
- **Rate Limiting**: Per-tenant request quotas and throttling
- **Authentication**: API key-based security
- **Monitoring**: Real-time metrics and health monitoring
- **Production Ready**: Docker, Kubernetes, and cloud deployment

## 📋 API Endpoints

### Authentication
All endpoints require API key authentication via `Authorization: Bearer <api_key>` header.

### Core Endpoints

#### `POST /v1/synthesize`
Synthesize text to speech with streaming support.

**Parameters:**
- `text` (string): Text to synthesize
- `voice_id` (string): Voice identifier (default: "default")
- `language` (string): Language code (default: "en")
- `ssml` (string, optional): SSML markup
- `streaming` (boolean): Enable streaming (default: true)

**Response:** Streaming audio data (WAV format)

#### `GET /v1/voices`
Get available voices for tenant.

**Response:**
```json
{
  "tenant_id": "tenant_abc123",
  "voices": [
    {
      "voice_id": "naija_female",
      "name": "Nigerian Female",
      "description": "High-quality Nigerian female voice",
      "language": "en",
      "is_preloaded": true
    }
  ],
  "total_count": 5
}
```

#### `POST /v1/voices/upload`
Upload reference audio for voice cloning.

**Parameters:**
- `voice_id` (string): Unique voice identifier
- `name` (string): Voice display name
- `description` (string): Voice description
- `language` (string): Language code
- `audio_file` (file): Reference audio file (WAV/MP3)

#### `GET /v1/health`
Health check with detailed status.

#### `GET /v1/tenant/stats`
Get tenant usage statistics.

## 🛠 Quick Start

### Local Development

1. **Clone and setup:**
```bash
cd /Users/odiadev/Desktop/tts/tts-service
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Start Redis (required for rate limiting):**
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

3. **Run the service:**
```bash
python -m src.server
```

4. **Test the API:**
```bash
# Health check
curl http://localhost:8000/v1/health

# Synthesize speech
curl -X POST http://localhost:8000/v1/synthesize \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -F "text=Hello from CallWaiting.ai TTS service" \
  -F "voice_id=naija_female" \
  --output output.wav
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

## 🔧 Configuration

### Environment Variables

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `REDIS_URL`: Redis connection URL
- `DATABASE_URL`: Database connection URL
- `TTS_AGREE_TO_CPML`: Coqui TTS license agreement (set to "1")

### Voice Configuration

Edit `config/voices.json` to customize preloaded voices:

```json
{
  "preloaded_voices": {
    "custom_voice": {
      "name": "Custom Voice",
      "description": "Custom voice description",
      "language": "en",
      "gender": "female",
      "accent": "nigerian"
    }
  }
}
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8000/v1/health
```

### Metrics (Admin only)
```bash
curl -H "Authorization: Bearer <admin_api_key>" \
  http://localhost:8000/v1/metrics
```

### Key Metrics
- **Time to first audio chunk**: ≤ 200ms
- **End-to-end latency**: ≤ 1 second for 3-5 second utterance
- **Error rate**: ≤ 0.1%
- **Concurrent streams**: ≥ 50 per GPU

## 🔐 Security

### API Keys
- Production keys: `sk_prod_*`
- Test keys: `sk_test_*`
- Admin keys: `sk_admin_*`

### Rate Limits
- Default: 1000 requests/minute, 10000 requests/hour
- Customizable per tenant

### Permissions
- `synthesize`: Generate speech
- `voices`: List voices
- `upload`: Upload custom voices
- `admin`: Access metrics and admin functions

## 🚀 Production Deployment

### Kubernetes
```bash
kubectl apply -f helm/
```

### AWS ECS
```bash
aws ecs create-service --cluster tts-cluster --service-name tts-service
```

### Google Cloud Run
```bash
gcloud run deploy tts-service --source . --port 8000
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Load Testing
```bash
# Install artillery
npm install -g artillery

# Run load test
artillery run tests/load/tts-load-test.yml
```

## 📈 Performance

### Benchmarks
- **Latency**: <200ms to first audio chunk
- **Throughput**: 50+ concurrent streams per GPU
- **Quality**: MOS ≥ 4.0 (human-like)
- **Uptime**: 99.9% availability target

### Optimization Tips
1. Use streaming mode for real-time applications
2. Cache frequently used phrases
3. Preload voice models in memory
4. Use GPU acceleration when available
5. Implement proper rate limiting

## 🤝 Integration Examples

### React Component
```jsx
const TTSComponent = () => {
  const synthesizeText = async (text) => {
    const response = await fetch('/v1/synthesize', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + apiKey,
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        text: text,
        voice_id: 'naija_female',
        streaming: 'true'
      })
    });
    
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    // Play audio
  };
};
```

### Python Client
```python
import requests

def synthesize_speech(text, voice_id="naija_female"):
    response = requests.post(
        'http://localhost:8000/v1/synthesize',
        headers={'Authorization': 'Bearer sk_test_1234567890abcdef'},
        data={
            'text': text,
            'voice_id': voice_id,
            'streaming': 'true'
        }
    )
    return response.content

# Usage
audio_data = synthesize_speech("Hello from CallWaiting.ai")
```

## 📝 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

For support and questions:
- Documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/v1/health
- Issues: Create GitHub issue

---

**Built with ❤️ for CallWaiting.ai using Coqui XTTS**
