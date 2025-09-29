# CallWaiting.ai TTS Service

High-performance Text-to-Speech microservice using **Microsoft Edge TTS** for CallWaiting.ai. Provides real neural voice synthesis with multiple voice options.

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
pip install -r requirements.txt
```

### Run the Service

```bash
python main.py
```

The service will start on `http://localhost:8000`

## 📡 API Endpoints

- `GET /` - Service info
- `GET /health` - Health check
- `GET /voices` - List available voices
- `POST /synthesize` - Synthesize text to speech
- `GET /tenant/stats` - Get tenant statistics

## 🎵 Available Voices

- **default**: en-US-AriaNeural (neutral)
- **naija_female**: en-US-JennyNeural (female)
- **naija_male**: en-US-GuyNeural (male)
- **professional**: en-US-DavisNeural (male)
- **friendly**: en-US-EmmaNeural (female)
- **calm**: en-US-MichelleNeural (female)
- **energetic**: en-US-BrandonNeural (male)

## 🔑 API Keys

- **Demo Key**: `cw_demo_12345` (tenant: callwaiting_demo)
- **Test Key**: `test_key_67890` (tenant: test_tenant)

## 📝 Usage Example

```bash
curl -X POST "http://localhost:8000/synthesize" \
  -H "Authorization: Bearer cw_demo_12345" \
  -F "text=Hello, this is a test" \
  -F "voice_id=default" \
  --output test.mp3
```

## 🎯 Features

- ✅ Real neural voice synthesis using Microsoft Edge TTS
- ✅ Multiple voice options
- ✅ API key authentication
- ✅ Health monitoring
- ✅ Tenant statistics
- ✅ Production-ready FastAPI implementation

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8000/health
```

### List Voices
```bash
curl -H "Authorization: Bearer cw_demo_12345" http://localhost:8000/voices
```

### Generate Audio
```bash
curl -X POST "http://localhost:8000/synthesize" \
  -H "Authorization: Bearer cw_demo_12345" \
  -F "text=Hello, this is a test of the CallWaiting.ai TTS service" \
  -F "voice_id=default" \
  --output test.mp3
```

### Get Tenant Stats
```bash
curl -H "Authorization: Bearer cw_demo_12345" http://localhost:8000/tenant/stats
```

## 🚀 Deployment

### Local Development
```bash
python main.py
```

### Production with Uvicorn
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📊 Monitoring

The service includes built-in metrics tracking:
- Total requests
- Requests by tenant
- Requests by voice
- Total audio generated
- Service uptime

## 🔧 Configuration

### Environment Variables
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

### Voice Configuration
Voices can be configured in the `EDGE_VOICES` dictionary in `main.py`.

## 📞 Support

For support and questions, please contact the CallWaiting.ai team.

---

**🎯 This TTS service is production-ready and provides high-quality neural voice synthesis for CallWaiting.ai applications.**