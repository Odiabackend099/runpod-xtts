# Testing Guide for TTS Service

## Test Coverage Areas

### 1. Authentication Tests
- Valid API key
- Invalid API key
- Missing API key
- Expired/disabled tenant
- Rate limiting

### 2. Synthesis Tests
- `/v1/synthesize` (streaming)
- `/v1/synthesize` (batch)
- `/v1/synthesize-url`
- Different voices
- Different languages
- SSML support
- Error handling

### 3. Storage Tests
- Local storage backend
- Supabase Storage backend
- Signed URL generation
- File serving

### 4. Usage Logging Tests
- Successful requests logged
- Failed requests logged
- Usage summary queries

### 5. Integration Tests
- Twilio voice playback
- WhatsApp audio delivery
- Web widget integration

---

## Quick Test Commands

### 1. Health Check
```bash
curl http://localhost:8000/v1/health
```

**Expected**: 200 OK with status: "healthy"

### 2. List Voices
```bash
curl -H "Authorization: Bearer sk_test_1234567890abcdef" \
  http://localhost:8000/v1/voices
```

**Expected**: JSON array of available voices

### 3. Synthesize (Batch)
```bash
curl -X POST "http://localhost:8000/v1/synthesize" \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -F "text=Hello from CallWaiting.ai TTS service" \
  -F "voice_id=default" \
  -F "streaming=false" \
  --output test-batch.wav
```

**Expected**: WAV file saved as test-batch.wav

### 4. Synthesize URL (Local Storage)
```bash
curl -X POST "http://localhost:8000/v1/synthesize-url" \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -F "text=This is a test of URL generation" \
  -F "voice_id=default"
```

**Expected**: JSON with `url` field

### 5. Synthesize URL (Supabase Storage)
```bash
export STORAGE_BACKEND=supabase
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=your-key

curl -X POST "http://localhost:8000/v1/synthesize-url" \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -F "text=Testing Supabase signed URLs" \
  -F "voice_id=default"
```

**Expected**: JSON with signed URL (https://xxx.supabase.co/...)

### 6. Download from Signed URL
```bash
# Get URL from previous command
SIGNED_URL="<paste-signed-url-here>"
curl "$SIGNED_URL" --output test-signed.wav
```

**Expected**: WAV file downloaded without authentication

### 7. Test Invalid API Key
```bash
curl -X POST "http://localhost:8000/v1/synthesize-url" \
  -H "Authorization: Bearer invalid_key" \
  -F "text=Test" \
  -F "voice_id=default"
```

**Expected**: 401 Unauthorized

### 8. Test Rate Limiting
```bash
# Make multiple rapid requests
for i in {1..10}; do
  curl -X POST "http://localhost:8000/v1/synthesize-url" \
    -H "Authorization: Bearer sk_test_1234567890abcdef" \
    -F "text=Rate limit test $i" \
    -F "voice_id=default"
done
```

**Expected**: Some requests may hit rate limit (429)

---

## Automated Test Script

Create `test_tts_service.sh`:

```bash
#!/bin/bash
set -e

BASE_URL="http://localhost:8000"
API_KEY="sk_test_1234567890abcdef"
TEST_TEXT="This is a test from the automated test suite"

echo "🧪 Starting TTS Service Tests"
echo "================================"

# Test 1: Health Check
echo "📋 Test 1: Health Check"
curl -s "$BASE_URL/v1/health" | jq .
echo "✅ Health check passed"
echo ""

# Test 2: List Voices
echo "📋 Test 2: List Voices"
VOICES=$(curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/v1/voices")
echo "$VOICES" | jq .
VOICE_COUNT=$(echo "$VOICES" | jq '.voices | length')
echo "✅ Found $VOICE_COUNT voices"
echo ""

# Test 3: Synthesize Batch
echo "📋 Test 3: Synthesize (Batch)"
curl -X POST "$BASE_URL/v1/synthesize" \
  -H "Authorization: Bearer $API_KEY" \
  -F "text=$TEST_TEXT" \
  -F "voice_id=default" \
  -F "streaming=false" \
  --output /tmp/test-batch.wav \
  -w "\nHTTP Status: %{http_code}\n"

if [ -f /tmp/test-batch.wav ]; then
  FILE_SIZE=$(wc -c < /tmp/test-batch.wav)
  echo "✅ Audio file created: $FILE_SIZE bytes"
else
  echo "❌ Audio file not created"
  exit 1
fi
echo ""

# Test 4: Synthesize URL
echo "📋 Test 4: Synthesize URL"
RESPONSE=$(curl -s -X POST "$BASE_URL/v1/synthesize-url" \
  -H "Authorization: Bearer $API_KEY" \
  -F "text=$TEST_TEXT" \
  -F "voice_id=default")
echo "$RESPONSE" | jq .

URL=$(echo "$RESPONSE" | jq -r '.url')
BACKEND=$(echo "$RESPONSE" | jq -r '.storage_backend')
echo "✅ URL generated: $URL"
echo "✅ Storage backend: $BACKEND"
echo ""

# Test 5: Invalid API Key
echo "📋 Test 5: Invalid API Key"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BASE_URL/v1/synthesize-url" \
  -H "Authorization: Bearer invalid_key_12345" \
  -F "text=Test" \
  -F "voice_id=default")

if [ "$HTTP_CODE" == "401" ]; then
  echo "✅ Invalid API key correctly rejected (401)"
else
  echo "❌ Expected 401, got $HTTP_CODE"
  exit 1
fi
echo ""

# Test 6: Tenant Stats
echo "📋 Test 6: Tenant Stats"
curl -s -H "Authorization: Bearer $API_KEY" "$BASE_URL/v1/tenant/stats" | jq .
echo "✅ Tenant stats retrieved"
echo ""

echo "================================"
echo "✅ All tests passed!"
```

Make it executable:
```bash
chmod +x test_tts_service.sh
./test_tts_service.sh
```

---

## Python Test Suite

Create `tests/test_api.py`:

```python
import pytest
import httpx
import os

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("TEST_API_KEY", "sk_test_1234567890abcdef")

@pytest.fixture
def client():
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {API_KEY}"}

@pytest.mark.asyncio
async def test_health_check(client):
    """Test health endpoint"""
    response = await client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "version" in data

@pytest.mark.asyncio
async def test_list_voices(client, auth_headers):
    """Test listing voices"""
    response = await client.get("/v1/voices", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "voices" in data
    assert len(data["voices"]) > 0

@pytest.mark.asyncio
async def test_synthesize_batch(client, auth_headers):
    """Test batch synthesis"""
    response = await client.post(
        "/v1/synthesize",
        headers=auth_headers,
        data={
            "text": "Test synthesis",
            "voice_id": "default",
            "streaming": "false"
        }
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0

@pytest.mark.asyncio
async def test_synthesize_url(client, auth_headers):
    """Test URL generation"""
    response = await client.post(
        "/v1/synthesize-url",
        headers=auth_headers,
        data={
            "text": "Test URL generation",
            "voice_id": "default"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "tenant_id" in data
    assert "storage_backend" in data

@pytest.mark.asyncio
async def test_invalid_api_key(client):
    """Test invalid API key rejection"""
    response = await client.get(
        "/v1/voices",
        headers={"Authorization": "Bearer invalid_key"}
    )
    assert response.status_code == 401

@pytest.mark.asyncio
async def test_tenant_stats(client, auth_headers):
    """Test tenant statistics"""
    response = await client.get("/v1/tenant/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "tenant_id" in data
    assert "requests_count" in data

# Run with: pytest tests/test_api.py -v
```

Install test dependencies:
```bash
pip install pytest pytest-asyncio httpx
```

Run tests:
```bash
pytest tests/test_api.py -v
```

---

## Load Testing with Apache Bench

```bash
# Install ab (Apache Bench)
# macOS: brew install httpd
# Ubuntu: apt-get install apache2-utils

# Test synthesize endpoint
ab -n 100 -c 10 \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -p test-payload.txt \
  -T "multipart/form-data" \
  http://localhost:8000/v1/synthesize-url
```

---

## Monitoring During Tests

### Watch Logs
```bash
# Terminal 1: Run service
python -m src.server

# Terminal 2: Watch logs
tail -f logs/tts_service.log
```

### Monitor Resource Usage
```bash
# CPU and memory
htop

# Disk I/O
iostat -x 1

# Network
netstat -an | grep 8000
```

---

## Expected Performance Metrics

- **Health check**: < 50ms
- **List voices**: < 100ms
- **Synthesize (5 words)**: 500ms - 2s (depending on model)
- **Storage upload (Supabase)**: 100-500ms
- **Signed URL generation**: 50-100ms

---

## Troubleshooting Test Failures

### Service Not Starting
- Check Python version (needs 3.10+)
- Verify all dependencies installed
- Check Redis is running
- Review startup logs

### Authentication Failures
- Verify API key format
- Check Supabase connection
- Review auth.py logs

### Storage Failures
- Local: Check directory permissions
- Supabase: Verify bucket exists and credentials
- Check STORAGE_BACKEND environment variable

### Synthesis Failures
- Check model is loaded (look for "TTS Service started successfully")
- Verify GPU/CPU resources available
- Check voice_id is valid

---

## CI/CD Integration

Add to GitHub Actions (`.github/workflows/test.yml`):

```yaml
name: TTS Service Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r tts-service/requirements.txt
          pip install pytest pytest-asyncio httpx
      
      - name: Run tests
        env:
          REDIS_URL: redis://localhost:6379/0
          AUDIO_STORAGE_DIR: /tmp/tts-audio
        run: |
          pytest tts-service/tests/ -v
```

---

## Next Steps

1. Run manual tests with provided commands
2. Execute automated test script
3. Run Python test suite
4. Perform load testing
5. Monitor metrics and logs
6. Document any issues found
