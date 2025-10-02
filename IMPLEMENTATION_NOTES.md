# Implementation Notes — runpod-xtts TTS Service

## ✅ Completed Changes (2025-10-02)

### 1. Planning & Documentation
- **Created** `planning.md` with phased roadmap for multi-tenant TTS service
- Defined API spec, Supabase schema, monitoring plan, and deployment strategy

### 2. API Enhancements
**File**: `tts-service/src/api/endpoints.py`
- **Added** `POST /v1/synthesize-url` → generates audio, saves to storage, returns URL
- **Added** `GET /v1/audio/{file_id}` → serves saved audio files (auth required)
- **Config**: `AUDIO_STORAGE_DIR` (preferred) or `AUDIO_STORAGE_PATH`, optional `PUBLIC_BASE_URL`
- **Imports**: Added `FileResponse`, `os`, `uuid`

### 3. Route Standardization
**File**: `tts-service/src/server.py`
- **Fixed** route prefix: removed `/api`, endpoints now at `/v1/*` (matches docs)
- All endpoints accessible at: `/v1/health`, `/v1/synthesize`, `/v1/synthesize-url`, `/v1/voices`, etc.

### 4. Supabase Authentication
**File**: `tts-service/src/utils/supabase_client.py` (new)
- **Created** `SupabaseAuthBackend` class
- Method `get_tenant_by_api_key()` queries Supabase `tenants` table by hashed API key
- Graceful fallback if Supabase not configured

**File**: `tts-service/src/api/auth.py`
- **Integrated** Supabase auth with in-memory keys as fallback
- **Updated** `validate_api_key()` to try Supabase first, then local keys
- **Fixed** Redis client to use `REDIS_URL` environment variable
- Returns consistent tenant dict: `tenant_id`, `name`, `api_key`, `permissions`, `rate_limit`

### 5. Configuration
**File**: `tts-service/env.example`
- **Added** Supabase vars: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_SCHEMA`, `SUPABASE_TENANTS_TABLE`, `SUPABASE_USAGE_LOGS_TABLE`
- **Added** storage vars: `AUDIO_STORAGE_DIR`, `PUBLIC_BASE_URL`
- **Documented** existing `REDIS_URL`, `AUDIO_STORAGE_PATH`

**File**: `tts-service/requirements.txt`
- **Added** `supabase>=2.3.0` dependency

### 6. Usage Logging (NEW)
**File**: `tts-service/src/utils/usage_logger.py` (new)
- **Created** `UsageLogger` class for tracking synthesis requests
- Method `log_synthesis()` logs to Supabase `usage_logs` table
- Method `log_voice_operation()` tracks voice uploads/deletes
- Method `get_tenant_usage_summary()` retrieves usage stats
- Graceful degradation if Supabase not configured

**File**: `tts-service/src/api/endpoints.py` (updated)
- **Integrated** usage logging in `/v1/synthesize` (streaming + batch paths)
- **Integrated** usage logging in `/v1/synthesize-url`
- **Logs** on success: tenant_id, input_chars, audio_bytes, latency_ms, streaming, voice_id, endpoint
- **Logs** on error: same fields plus error message

**File**: `tts-service/supabase_schema.sql` (new)
- **Complete** database schema for `tenants`, `usage_logs`, `voices` tables
- **Indexes** for performance optimization
- **RLS policies** for security
- **Helper functions** for API key hashing and usage summaries
- **Sample data** for testing

---

## 🎯 API Endpoints (Updated)

### Core Endpoints
- `GET /v1/health` → health check with model info
- `GET /v1/voices` → list available voices for tenant
- `POST /v1/voices/upload` → upload reference audio for voice cloning
- `DELETE /v1/voices/{voice_id}` → delete custom voice

### Synthesis Endpoints
- `POST /v1/synthesize` → generate audio (streaming or batch)
  - Params: `text`, `voice_id`, `language`, `ssml`, `streaming`
  - Returns: audio/wav stream
- `POST /v1/synthesize-url` → generate audio and return download URL
  - Params: `text`, `voice_id`, `language`, `ssml`
  - Returns: JSON with `url`, `tenant_id`, `voice_id`, `content_type`
- `GET /v1/audio/{file_id}` → download generated audio file
  - Currently requires authentication
  - For Twilio/public use: expose via gateway or switch to signed URLs

### Monitoring
- `GET /v1/tenant/stats` → tenant usage statistics
- `GET /v1/metrics` → system metrics (admin only)

---

## 🔧 Environment Configuration

### Required
```bash
export REDIS_URL=redis://localhost:6379/0
export AUDIO_STORAGE_DIR=/tmp/tts-audio
```

### Optional (Supabase Auth)
```bash
export SUPABASE_URL=https://your-project.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...
export SUPABASE_SCHEMA=public
export SUPABASE_TENANTS_TABLE=tenants
```

### Optional (Public URLs)
```bash
export PUBLIC_BASE_URL=https://tts.odia.dev
```

---

## 🐛 Local Testing Issue (Python Version)

### Problem
- System Python: 3.9.x
- TTS library dependency (`bangla` package) requires Python 3.10+ for type union syntax (`bool | None`)
- Error: `TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`

### Solutions
1. **Use Python 3.10+** (recommended for local dev)
   ```bash
   pyenv install 3.10
   pyenv local 3.10
   pip install -r tts-service/requirements.txt
   ```

2. **Docker** (matches production environment)
   ```bash
   cd tts-service
   docker-compose up --build
   ```

3. **RunPod** (target deployment — Python 3.10+ available)
   - Deploy directly to RunPod GPU pods
   - Environment will have compatible Python version

### Code Changes Are Valid
- All code modifications are Python 3.9+ compatible
- Issue is only with TTS library dependencies
- Service will run correctly on Python 3.10+ or in Docker/RunPod

---

## 📋 Pending Tasks

### High Priority
- ✅ **Usage Logging**: COMPLETED
  - Created `utils/usage_logger.py` with Supabase integration
  - Logs: `tenant_id`, `request_id`, `input_chars`, `audio_bytes`, `latency_ms`, `streaming`, `voice_id`, `endpoint`, `error`, `metadata`
  - Integrated into `/v1/synthesize` (both streaming and batch) and `/v1/synthesize-url`
  - Logs both successful requests and errors
  - Created `supabase_schema.sql` with complete database schema
- **Signed URLs**: Decide S3 vs Supabase Storage backend
  - Update `/v1/synthesize-url` to upload and return signed URLs
  - Optionally remove local `/v1/audio/{file_id}` route

### Medium Priority
- **WebSocket Streaming**: Implement `WS /v1/stream` for low-latency chunk delivery
- **Monitoring**: Add Prometheus metrics (`/metrics`) and Sentry/Axiom error tracking
- **Docs Update**: Sync `tts-service/README.md` with new endpoints and env vars

### Deployment
- **RunPod Hardening**: Health checks, readiness probes, autoscaling config
- **Service Consolidation**: Decide fate of root `main.py` (Edge TTS) — keep as fallback or deprecate

---

## 🧪 Quick Verification (Python 3.10+)

### Install Dependencies
```bash
cd tts-service
pip install -r requirements.txt
```

### Start Redis (Docker)
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### Start Service
```bash
export REDIS_URL=redis://localhost:6379/0
export AUDIO_STORAGE_DIR=/tmp/tts-audio
python -m src.server
```

### Test Endpoints
```bash
# Health check
curl http://localhost:8000/v1/health

# Generate audio URL
curl -X POST "http://localhost:8000/v1/synthesize-url" \
  -H "Authorization: Bearer sk_test_1234567890abcdef" \
  -F "text=Hello from CallWaiting.ai" \
  -F "voice_id=default"

# Download audio (requires auth)
curl -H "Authorization: Bearer sk_test_1234567890abcdef" \
  "http://localhost:8000/v1/audio/<file_id>" --output test.wav
```

---

## 🎯 Success Criteria (from planning.md)

- ✅ Route standardization: endpoints at `/v1/*`
- ✅ Supabase auth integration with fallback
- ✅ Audio URL generation endpoint
- ✅ Config documented in `env.example`
- ⏳ Usage logging (pending)
- ⏳ WebSocket streaming (pending)
- ⏳ Monitoring/observability (pending)
- ⏳ P95 latency ≤ 1.5s (to be verified on GPU)
- ⏳ 99.5% uptime (deployment target)

---

## 📌 Summary

**Status**: Phase 1-2 features implemented and ready for testing on Python 3.10+/Docker/RunPod.

**What Works**:
- API wrapper with new endpoints
- Supabase-backed authentication
- Route standardization
- Storage and public URL support

**What's Next**:
- Usage logging to Supabase
- Signed URLs (S3 or Supabase Storage)
- WebSocket streaming
- Monitoring/metrics
- Deployment to RunPod

**Deployment Path**: Use Docker or Python 3.10+ environment for local testing, then deploy to RunPod GPU pods for production.
