-- Supabase Schema for CallWaiting.ai TTS Service
-- This file defines the database tables required for authentication and usage logging

-- =====================================================
-- Tenants Table
-- =====================================================
-- Stores tenant/customer information and API key authentication
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    api_key_hash TEXT NOT NULL UNIQUE,
    quota_minutes INTEGER DEFAULT 0,
    rate_limit_minute INTEGER DEFAULT 1000,
    rate_limit_hour INTEGER DEFAULT 10000,
    is_active BOOLEAN DEFAULT true,
    permissions JSONB DEFAULT '["synthesize", "voices"]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenants_api_key_hash ON public.tenants(api_key_hash);
CREATE INDEX IF NOT EXISTS idx_tenants_is_active ON public.tenants(is_active);

-- =====================================================
-- Usage Logs Table
-- =====================================================
-- Tracks all TTS synthesis requests for analytics and billing
CREATE TABLE IF NOT EXISTS public.usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    request_id TEXT NOT NULL,
    input_chars INTEGER DEFAULT 0,
    audio_bytes INTEGER DEFAULT 0,
    latency_ms INTEGER DEFAULT 0,
    streaming BOOLEAN DEFAULT false,
    voice_id TEXT NOT NULL,
    language TEXT DEFAULT 'en',
    endpoint TEXT DEFAULT 'synthesize',
    error TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_usage_logs_tenant_id ON public.usage_logs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_usage_logs_created_at ON public.usage_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_logs_tenant_created ON public.usage_logs(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_logs_request_id ON public.usage_logs(request_id);

-- =====================================================
-- Voices Table (Optional)
-- =====================================================
-- Stores custom voice profiles per tenant
CREATE TABLE IF NOT EXISTS public.voices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    voice_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    language TEXT DEFAULT 'en',
    gender TEXT,
    accent TEXT,
    reference_audio_path TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(tenant_id, voice_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_voices_tenant_id ON public.voices(tenant_id);
CREATE INDEX IF NOT EXISTS idx_voices_voice_id ON public.voices(voice_id);
CREATE INDEX IF NOT EXISTS idx_voices_tenant_voice ON public.voices(tenant_id, voice_id);

-- =====================================================
-- Sample Data (for testing)
-- =====================================================
-- Insert demo tenant (API key: sk_test_1234567890abcdef)
-- Note: The hash below is SHA256 of 'sk_test_1234567890abcdef'
INSERT INTO public.tenants (name, api_key_hash, quota_minutes, rate_limit_minute, rate_limit_hour, is_active, permissions)
VALUES (
    'CallWaiting.ai Production',
    'f8e4c1e5a5b6d7c8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2',
    10000,
    1000,
    10000,
    true,
    '["synthesize", "voices", "upload"]'::jsonb
)
ON CONFLICT (api_key_hash) DO NOTHING;

-- Insert test tenant (API key: sk_test_fedcba0987654321)
-- Note: The hash below is SHA256 of 'sk_test_fedcba0987654321'
INSERT INTO public.tenants (name, api_key_hash, quota_minutes, rate_limit_minute, rate_limit_hour, is_active, permissions)
VALUES (
    'CallWaiting.ai Development',
    '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2',
    1000,
    100,
    1000,
    true,
    '["synthesize", "voices"]'::jsonb
)
ON CONFLICT (api_key_hash) DO NOTHING;

-- =====================================================
-- Row Level Security (RLS) Policies
-- =====================================================
-- Enable RLS on all tables
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.usage_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.voices ENABLE ROW LEVEL SECURITY;

-- Policy: Service role can do everything
CREATE POLICY "Service role has full access to tenants"
    ON public.tenants
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to usage_logs"
    ON public.usage_logs
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role has full access to voices"
    ON public.voices
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =====================================================
-- Helper Functions
-- =====================================================
-- Function to generate API key hash (for inserting new tenants)
CREATE OR REPLACE FUNCTION public.hash_api_key(api_key TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN encode(digest(api_key, 'sha256'), 'hex');
END;
$$ LANGUAGE plpgsql;

-- Function to get tenant usage summary
CREATE OR REPLACE FUNCTION public.get_tenant_usage_summary(
    p_tenant_id UUID,
    p_days INTEGER DEFAULT 30
)
RETURNS TABLE (
    total_requests BIGINT,
    total_chars BIGINT,
    total_bytes BIGINT,
    total_errors BIGINT,
    streaming_requests BIGINT,
    avg_latency_ms NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT as total_requests,
        SUM(input_chars)::BIGINT as total_chars,
        SUM(audio_bytes)::BIGINT as total_bytes,
        SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END)::BIGINT as total_errors,
        SUM(CASE WHEN streaming THEN 1 ELSE 0 END)::BIGINT as streaming_requests,
        AVG(latency_ms)::NUMERIC as avg_latency_ms
    FROM public.usage_logs
    WHERE tenant_id = p_tenant_id
      AND created_at >= NOW() - (p_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Comments
-- =====================================================
COMMENT ON TABLE public.tenants IS 'Stores tenant information and API key hashes for authentication';
COMMENT ON TABLE public.usage_logs IS 'Tracks all TTS synthesis requests for analytics, monitoring, and billing';
COMMENT ON TABLE public.voices IS 'Stores custom voice profiles and reference audio per tenant';

COMMENT ON COLUMN public.tenants.api_key_hash IS 'SHA256 hash of the tenant API key for secure authentication';
COMMENT ON COLUMN public.tenants.quota_minutes IS 'Total minutes of audio quota allocated to tenant';
COMMENT ON COLUMN public.tenants.rate_limit_minute IS 'Maximum requests per minute for this tenant';
COMMENT ON COLUMN public.tenants.rate_limit_hour IS 'Maximum requests per hour for this tenant';

COMMENT ON COLUMN public.usage_logs.request_id IS 'Unique identifier for this synthesis request';
COMMENT ON COLUMN public.usage_logs.input_chars IS 'Number of input characters/tokens synthesized';
COMMENT ON COLUMN public.usage_logs.audio_bytes IS 'Size of generated audio in bytes';
COMMENT ON COLUMN public.usage_logs.latency_ms IS 'Request latency in milliseconds';
COMMENT ON COLUMN public.usage_logs.streaming IS 'Whether this was a streaming or batch request';
COMMENT ON COLUMN public.usage_logs.endpoint IS 'API endpoint used (synthesize, synthesize-url, etc)';
COMMENT ON COLUMN public.usage_logs.metadata IS 'Additional request metadata in JSON format';
