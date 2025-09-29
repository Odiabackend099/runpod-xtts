# CallWaiting.ai TTS Service - Client Integration

## Environment Setup for Local TTS Service

This guide shows you how to integrate and call the CallWaiting.ai TTS service locally.

## Quick Start

### 1. Environment Configuration

Copy the environment template and customize it:

```bash
cp env.example .env
```

### 2. Key Environment Variables

```bash
# Server Configuration
TTS_HOST=localhost
TTS_PORT=8000
TTS_API_KEY=cw_demo_12345

# TTS Settings
TTS_DEFAULT_VOICE=default
TTS_DEFAULT_LANGUAGE=en
TTS_AUDIO_FORMAT=mp3

# Available Voices
TTS_VOICES=default,naija_female,naija_male,professional,friendly,calm,energetic
```

### 3. Start the TTS Service

```bash
python3 real_tts_server.py
```

### 4. Test the Client

```bash
python3 tts_client.py
```

## Client Usage Examples

### Basic Python Client

```python
from tts_client import TTSServiceClient

# Initialize client
client = TTSServiceClient()

# Health check
health = client.health_check()
print(f"Service status: {health['status']}")

# Synthesize text
audio_data = client.synthesize("Hello, this is a test.")
if audio_data:
    with open("output.mp3", "wb") as f:
        f.write(audio_data)

# Get available voices
voices = client.get_voices()
for voice in voices['voices']:
    print(f"Voice: {voice['id']} - {voice['name']}")
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/v1/health

# Get voices
curl -H "Authorization: Bearer cw_demo_12345" \
     http://localhost:8000/v1/voices

# Synthesize text
curl -X POST "http://localhost:8000/v1/synthesize" \
     -H "Authorization: Bearer cw_demo_12345" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "text=Hello, this is a test&voice_id=default&language=en" \
     --output test.mp3

# Generate demo audio
curl -X POST "http://localhost:8000/v1/generate-demo-audio" \
     -H "Authorization: Bearer cw_demo_12345" \
     --output demo_audio.json
```

### JavaScript/Node.js Example

```javascript
const axios = require('axios');

const ttsConfig = {
    baseURL: 'http://localhost:8000/v1',
    headers: {
        'Authorization': 'Bearer cw_demo_12345',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
};

// Synthesize text
async function synthesizeText(text, voiceId = 'default') {
    try {
        const response = await axios.post('/synthesize', {
            text: text,
            voice_id: voiceId,
            language: 'en'
        }, ttsConfig);
        
        return response.data;
    } catch (error) {
        console.error('TTS synthesis failed:', error.message);
        return null;
    }
}

// Usage
synthesizeText("Hello, this is a test of the TTS service.")
    .then(audioData => {
        if (audioData) {
            console.log('Audio generated successfully');
        }
    });
```

## Available Voices

| Voice ID | Name | Description |
|----------|------|-------------|
| `default` | Default | en-US-AriaNeural |
| `naija_female` | Naija Female | en-US-JennyNeural |
| `naija_male` | Naija Male | en-US-GuyNeural |
| `professional` | Professional | en-US-DavisNeural |
| `friendly` | Friendly | en-US-EmmaNeural |
| `calm` | Calm | en-US-MichelleNeural |
| `energetic` | Energetic | en-US-BrianNeural |

## API Endpoints

- `GET /v1/health` - Health check
- `GET /v1/voices` - Get available voices
- `POST /v1/synthesize` - Synthesize text to speech
- `POST /v1/synthesize/streaming` - Stream audio synthesis
- `GET /v1/tenant/stats` - Get tenant statistics
- `POST /v1/generate-demo-audio` - Generate demo audio files

## Configuration Options

### Environment Variables

```bash
# Server
TTS_HOST=localhost
TTS_PORT=8000
TTS_API_KEY=cw_demo_12345

# TTS Settings
TTS_DEFAULT_VOICE=default
TTS_DEFAULT_LANGUAGE=en
TTS_AUDIO_FORMAT=mp3

# Timeouts
TTS_TIMEOUT=30
TTS_STREAMING_TIMEOUT=60

# Retry Settings
TTS_MAX_RETRIES=3
TTS_RETRY_DELAY=1.0

# Debug
TTS_DEBUG=false
TTS_VERBOSE=false
```

### Client Configuration

The `client_config.py` file contains all configuration options:

```python
from client_config import get_config

config = get_config()
print(f"Server URL: {config.BASE_URL}")
print(f"API Key: {config.API_KEY}")
print(f"Available voices: {list(config.VOICES.keys())}")
```

## Error Handling

```python
from tts_client import TTSServiceClient

client = TTSServiceClient()

try:
    audio_data = client.synthesize("Test text")
    if audio_data:
        print("Success!")
    else:
        print("Synthesis failed")
except Exception as e:
    print(f"Error: {e}")
```

## Streaming Audio

```python
# Stream audio synthesis
for chunk in client.synthesize_streaming("Long text here..."):
    if chunk:
        # Process audio chunk
        process_audio_chunk(chunk)
```

## Multi-tenant Support

The service supports multiple tenants with different API keys:

- `cw_demo_12345` - Demo tenant (callwaiting_demo)
- `test_key_67890` - Test tenant (test_tenant)

Each tenant has access to different voices and rate limits.

## Production Deployment

For production use:

1. Change the API keys in `.env`
2. Set up proper authentication
3. Configure rate limiting
4. Set up monitoring and logging
5. Use HTTPS in production

## Troubleshooting

### Service Not Responding
```bash
# Check if service is running
curl http://localhost:8000/v1/health

# Check logs
tail -f logs/tts_service.log
```

### Authentication Issues
```bash
# Verify API key
curl -H "Authorization: Bearer cw_demo_12345" \
     http://localhost:8000/v1/voices
```

### Audio Quality Issues
- Check voice selection
- Verify text input
- Check audio format settings

## Support

For issues or questions:
- Check the service logs
- Verify environment configuration
- Test with the provided client examples
- Review the API documentation at http://localhost:8000/docs
