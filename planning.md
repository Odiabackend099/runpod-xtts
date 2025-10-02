# planning.md — runpod-xtts (CallWaiting.ai TTS)

## 0) Current State (as of 2025-10-02)

- tts-service/ (primary): FastAPI service using Coqui XTTS with streaming, auth, and rate limiting
  - API: defined in `tts-service/src/api/endpoints.py` (paths like `/v1/synthesize`, `/v1/voices`, `/v1/tenant/stats`)
  - Auth/Rate limit: `tts-service/src/api/auth.py` (in-memory API keys + Redis-based rate limiting)
  - Server: `tts-service/src/server.py` mounts API app router with prefix `/api` → results in paths like `/api/v1/...` (docs and code references mix `/v1` vs `/api/v1`)
- Root service (secondary): `main.py` uses Microsoft Edge TTS; demo keys and simple metrics (non-Coqui). Consider deprecating or keep as fallback.

Decision: adopt `tts-service/` (Coqui XTTS) as the primary production service. Root `main.py` becomes an optional fallback service or is removed post cutover.

---

## 1) Objectives

Transform repo into a multi-tenant, secure, low-latency TTS microservice powering CallWaiting.ai voice agents (phone, WhatsApp, web) at `tts.odia.dev`.

Key outcomes:
- P95 silence→speech ≤ 1.5s
- Auth: 0 unauthenticated calls succeed
- ≥90% of requests logged by tenant in Supabase
- Stable streaming for ≥80% calls with no dropout
- 99.5% uptime on RunPod

---

## 2) Phases & Deliverables

### Phase 1 — Service Consolidation & API Surface
- Adopt `tts-service` as the single entry point.
- Fix route mismatch:
  - Option A (preferred): serve endpoints at `/v1/*` (no `/api` prefix). Update `src/server.py` to mount without extra prefix or expose `api_app` directly.
  - Update docs (`tts-service/README.md`) and tests accordingly.
- Add `POST /v1/synthesize-url`: returns signed URL to generated audio (WAV 24kHz by default; MP3 optional).
- Ensure consistent media types: default WAV 24kHz for streaming/batch.

Acceptance:
- `GET /v1/health`, `POST /v1/synthesize`, `GET /v1/voices` reachable without `/api` prefix.
- `POST /v1/synthesize-url` returns signed URL and is covered by a test.

### Phase 2 — Security & Multi-Tenancy (Supabase)
- Replace in-memory API keys in `src/api/auth.py` with Supabase-backed auth.
  - Tables: `tenants(id, name, api_key_hash, quota_minutes, is_active, created_at)`
  - Optional: `permissions` per tenant.
- Rate limiting via Redis (already present) with per-tenant limits stored in Supabase.
- Env-driven config for Supabase URL/keys.

Acceptance:
- Invalid/disabled keys rejected.
- Per-tenant rate limits effective; limits configurable via DB.

### Phase 3 — Usage Logging & CRM Integration
- Schema additions:
  - `usage_logs(id, tenant_id, request_id, input_chars, audio_bytes, latency_ms, streaming, voice_id, created_at)`
  - `voices(tenant_id, voice_id, name, language, meta, reference_audio_path, created_at)`
- Log each `/v1/synthesize` and `/v1/synthesize-url` request.
- Expose usage summaries to CallWaiting.ai dashboard (downstream integration).

Acceptance:
- ≥90% of successful requests produce a `usage_logs` row with latency and size.

### Phase 4 — Streaming & Telephony
- WebSocket streaming endpoint: `WS /v1/stream` for low-latency chunking using existing streaming machinery.
- Twilio: return `<Play>` URLs pointing to `/v1/synthesize-url`.
- WhatsApp/n8n: example workflow to generate and attach voice.

Acceptance:
- End-to-end demo: Twilio call plays generated audio from `/v1/synthesize-url`.
- WebSocket streaming works with time-to-first-chunk ≤ 200ms on GPU pod.

### Phase 5 — Monitoring, Observability, and Scaling
- Metrics: Prometheus exporter (latency, request counts, bytes, active streams, GPU mem if available).
- Errors: Sentry or Axiom instrumentation.
- Deployment: Docker + RunPod GPU pods, autoscaling via gateway; health checks and readiness probes.

Acceptance:
- `/metrics` exposes Prometheus counters/histograms.
- Errors captured in Sentry/Axiom with tenant context (no PII).

---

## 3) API Spec (target)

- `GET /v1/health` → status, model info, uptime
- `GET /v1/voices` → voices for tenant
- `POST /v1/voices/upload` → reference audio (permission: upload)
- `DELETE /v1/voices/{voice_id}` → delete voice
- `POST /v1/synthesize` → audio (WAV by default; `streaming` true/false)
- `POST /v1/synthesize-url` → signed URL (WAV/MP3)
- `WS /v1/stream` → stream audio frames

Auth: `Authorization: Bearer <api_key>`

---

## 4) Configuration

Environment variables (representative):
- Core
  - `HOST` (default 0.0.0.0)
  - `PORT` (default 8000)
  - `WORKERS` (prod)
  - `LOG_LEVEL` (info)
- Models
  - `XTTS_MODEL_PATH`
  - `VOICES_DIR`
- Supabase
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY` (client) or `SUPABASE_SERVICE_ROLE_KEY` (server ops)
  - `SUPABASE_SCHEMA` (optional)
- Redis
  - `REDIS_URL` (e.g., redis://host:6379/0)
- Storage (choose one)
  - S3: `S3_BUCKET`, `S3_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
  - Supabase Storage: `SUPABASE_BUCKET`
- Telephony
  - `PUBLIC_BASE_URL` (for signed URLs used by Twilio)
- Observability
  - `SENTRY_DSN` or `AXIOM_TOKEN`

---

## 5) Data Model (Supabase/Postgres)

- `tenants`
  - id (uuid), name, api_key_hash (text), quota_minutes (int), rate_limit_minute (int), rate_limit_hour (int), is_active (bool), created_at (timestamptz)
- `voices`
  - tenant_id (uuid), voice_id (text pk within tenant), name, language, meta (jsonb), reference_audio_path (text), created_at
- `usage_logs`
  - id (uuid), tenant_id (uuid), request_id (text), input_chars (int), audio_bytes (int), latency_ms (int), streaming (bool), voice_id (text), error (text null), created_at

Indexes on `usage_logs(tenant_id, created_at)`.

---

## 6) Implementation Notes

- Keep streaming path hot: preload model on startup (`startup_event`) and maintain cache of frequent voices.
- Set default audio to WAV 24kHz for streaming; MP3 optional for file URLs.
- Validate SSML and sanitize inputs to avoid injection.
- Ensure `/v1/*` paths align in `src/server.py` and docs/tests.
- Consider removing root `main.py` after cutover; otherwise, keep as fallback under separate process/port.

---

## 7) Testing

- Unit: auth (valid/invalid key), rate limiting, voice manager, SSML parser.
- Integration: `/v1/synthesize` (batch + streaming), `/v1/synthesize-url`, `/v1/voices`.
- Load: 100 concurrent → P95 ≤ 1.5s on RunPod GPU.
- Telephony: Twilio `<Play>` round-trip check using public URL.

---

## 8) Deployment (RunPod)

- Build GPU image from `tts-service/` Dockerfile.
- Provide envs via RunPod template (Redis URL, Supabase, Storage, Sentry, PUBLIC_BASE_URL).
- Health/readiness probes against `/v1/health`.
- Gateway in front for TLS + autoscaling.

---

## 9) Timeline (indicative)

- Phase 1: 1–2 days
- Phase 2: 1–2 days
- Phase 3: 1–2 days
- Phase 4: 2–4 days
- Phase 5: 1–2 days

---

## 10) Open Questions

- Storage backend preference (S3 vs Supabase Storage) for `/synthesize-url`?
- Keep Edge TTS fallback or fully deprecate?
- Tenant provisioning flow (manual vs automated via dashboard)?
