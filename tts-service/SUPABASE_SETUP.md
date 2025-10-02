# Supabase Setup Guide for TTS Service

This guide walks through setting up Supabase for authentication and usage logging in the CallWaiting.ai TTS Service.

## Prerequisites

- Supabase account (free tier works)
- Access to Supabase SQL Editor

## 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create a new project
3. Note your project URL and service role key

## 2. Run Database Schema

1. Open the Supabase SQL Editor
2. Copy the contents of `supabase_schema.sql`
3. Execute the SQL to create:
   - `tenants` table (authentication)
   - `usage_logs` table (usage tracking)
   - `voices` table (custom voice profiles)
   - Indexes and policies
   - Helper functions

## 3. Create Storage Bucket (for signed URLs)

1. Go to Storage in Supabase dashboard
2. Create a new bucket:
   - Name: `tts-audio`
   - Public: **No** (we'll use signed URLs)
3. Set bucket policies:
   - Allow service_role to upload/read/delete
   - No public access (signed URLs provide temporary access)

## 4. Configure Environment Variables

Add these to your `.env` file or environment:

```bash
# Required
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGc...your-service-role-key

# Optional (defaults shown)
SUPABASE_SCHEMA=public
SUPABASE_TENANTS_TABLE=tenants
SUPABASE_USAGE_LOGS_TABLE=usage_logs

# Storage Backend (choose "supabase" for signed URLs)
STORAGE_BACKEND=supabase
SUPABASE_STORAGE_BUCKET=tts-audio
SIGNED_URL_EXPIRY_SECONDS=3600
```

## 5. Create Your First Tenant

### Option A: Using Supabase Dashboard

1. Go to Table Editor → `tenants`
2. Insert a new row:
   - `name`: Your organization name
   - `api_key_hash`: SHA256 hash of your API key
   - `quota_minutes`: 10000
   - `rate_limit_minute`: 1000
   - `rate_limit_hour`: 10000
   - `is_active`: true
   - `permissions`: `["synthesize", "voices", "upload"]`

### Option B: Using SQL

Generate API key hash and insert tenant:

```sql
-- Replace 'your-api-key-here' with your actual API key
INSERT INTO public.tenants (name, api_key_hash, quota_minutes, rate_limit_minute, rate_limit_hour, is_active, permissions)
VALUES (
    'Your Organization',
    public.hash_api_key('your-api-key-here'),
    10000,
    1000,
    10000,
    true,
    '["synthesize", "voices", "upload"]'::jsonb
);
```

### Generate API Key Hash (Python)

If you need to generate the hash locally:

```python
import hashlib

api_key = "sk_prod_your_secret_key_here"
api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()
print(f"API Key Hash: {api_key_hash}")
```

## 5. Test Authentication

```bash
curl -X POST "http://localhost:8000/v1/synthesize-url" \
  -H "Authorization: Bearer your-api-key-here" \
  -F "text=Test authentication" \
  -F "voice_id=default"
```

If authentication works, you should get a JSON response with a URL.

## 6. Verify Usage Logging

After making a few requests, check the `usage_logs` table:

```sql
SELECT 
    tenant_id,
    request_id,
    input_chars,
    audio_bytes,
    latency_ms,
    streaming,
    voice_id,
    endpoint,
    created_at
FROM public.usage_logs
ORDER BY created_at DESC
LIMIT 10;
```

## 7. Query Usage Summary

Use the built-in helper function:

```sql
-- Get 30-day usage summary for a tenant
SELECT * FROM public.get_tenant_usage_summary(
    'your-tenant-uuid-here',
    30
);
```

## Common Issues

### Issue: "Invalid API key"

**Cause**: API key hash doesn't match any tenant in database

**Solution**:
1. Verify the API key is correct
2. Ensure the hash in database matches: `SELECT api_key_hash FROM public.tenants;`
3. Re-generate hash if needed

### Issue: Usage logs not appearing

**Cause**: Supabase environment variables not set

**Solution**:
1. Check `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set
2. Look for log message: "✅ Usage logger initialized with Supabase"
3. If you see "⚠️ Usage logger disabled", check env vars

### Issue: Permission denied on tables

**Cause**: Row Level Security policies not set correctly

**Solution**:
1. Ensure you're using the **service role key**, not the anon key
2. Verify RLS policies allow service_role access:
```sql
SELECT * FROM pg_policies WHERE tablename IN ('tenants', 'usage_logs', 'voices');
```

## API Key Best Practices

1. **Format**: Use prefixes for clarity
   - Production: `sk_prod_...`
   - Test: `sk_test_...`
   - Development: `sk_dev_...`

2. **Length**: At least 32 characters of randomness

3. **Generation**:
```python
import secrets
api_key = f"sk_prod_{secrets.token_urlsafe(32)}"
```

4. **Storage**: 
   - Store only the hash in database
   - Give the actual key to the tenant once (they cannot recover it)
   - Never log or expose the actual key

## Monitoring Queries

### Daily request count
```sql
SELECT 
    DATE(created_at) as date,
    COUNT(*) as requests,
    SUM(audio_bytes) / 1024 / 1024 as total_mb
FROM public.usage_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Error rate by tenant
```sql
SELECT 
    t.name,
    COUNT(*) as total_requests,
    SUM(CASE WHEN ul.error IS NOT NULL THEN 1 ELSE 0 END) as errors,
    ROUND(100.0 * SUM(CASE WHEN ul.error IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate_pct
FROM public.usage_logs ul
JOIN public.tenants t ON ul.tenant_id = t.id
WHERE ul.created_at >= NOW() - INTERVAL '24 hours'
GROUP BY t.name
ORDER BY error_rate_pct DESC;
```

### Most popular voices
```sql
SELECT 
    voice_id,
    COUNT(*) as usage_count,
    ROUND(AVG(latency_ms)) as avg_latency_ms
FROM public.usage_logs
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY voice_id
ORDER BY usage_count DESC
LIMIT 10;
```

## Next Steps

1. Set up Supabase Storage for audio files (signed URLs)
2. Configure Supabase Auth for user management (optional)
3. Set up Supabase Edge Functions for webhooks (optional)
4. Enable Supabase Realtime for live dashboards (optional)

## Support

- Supabase Docs: https://supabase.com/docs
- TTS Service Issues: Create GitHub issue
- CallWaiting.ai Support: Contact team
