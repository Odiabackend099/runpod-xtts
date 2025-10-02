"""
Supabase client helper for authentication and tenant lookups.
"""
import os
import logging
import hashlib
from typing import Optional, Dict, Any

try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover - supabase may not be installed in some environments
    create_client = None
    Client = None

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_SCHEMA = os.getenv("SUPABASE_SCHEMA", "public")
TENANTS_TABLE = os.getenv("SUPABASE_TENANTS_TABLE", "tenants")


def _is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and create_client is not None)


class SupabaseAuthBackend:
    def __init__(self) -> None:
        self.enabled: bool = _is_configured()
        self.client: Optional[Client] = None
        if self.enabled:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase client: {e}")
                self.enabled = False

    @staticmethod
    def hash_api_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode()).hexdigest()

    def get_tenant_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        if not self.enabled or not self.client or not api_key:
            return None
        try:
            api_key_hash = self.hash_api_key(api_key)
            # Query tenants table by hashed key
            res = (
                self.client
                .table(TENANTS_TABLE)
                .select("*")
                .eq("api_key_hash", api_key_hash)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            data = getattr(res, "data", None) or []
            if not data:
                return None
            row = data[0]
            rate_limit = {
                "requests_per_minute": row.get("rate_limit_minute", 1000),
                "requests_per_hour": row.get("rate_limit_hour", 10000),
            }
            permissions = row.get("permissions") or ["synthesize", "voices"]
            return {
                "tenant_id": row.get("id") or row.get("tenant_id"),
                "name": row.get("name") or "Tenant",
                "permissions": permissions,
                "rate_limit": rate_limit,
                "created_at": row.get("created_at"),
                "is_active": True,
                # include api_key so downstream checks can reference it if needed
                "api_key": api_key,
            }
        except Exception as e:  # pragma: no cover - defensive
            logger.error(f"Supabase get_tenant_by_api_key error: {e}")
            return None


# Singleton instance used by auth module
supabase_auth = SupabaseAuthBackend()
