"""
Authentication and Authorization Module
Handles API key validation, tenant isolation, and rate limiting
"""

import hashlib
import time
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import logging
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import json
from ..utils.supabase_client import supabase_auth

logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Redis client for rate limiting and caching (supports REDIS_URL)
_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_client = redis.from_url(_redis_url, decode_responses=True)

class APIKeyManager:
    """Manages API keys and tenant authentication"""
    
    def __init__(self):
        self.api_keys = {}  # In production, use database
        self._load_api_keys()
    
    def _load_api_keys(self):
        """Load API keys (in production, load from database)"""
        # Sample API keys for different tenants
        self.api_keys = {
            "sk_test_1234567890abcdef": {
                "tenant_id": "tenant_abc123",
                "name": "CallWaiting.ai Production",
                "permissions": ["synthesize", "voices", "upload"],
                "rate_limit": {
                    "requests_per_minute": 1000,
                    "requests_per_hour": 10000
                },
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            },
            "sk_test_fedcba0987654321": {
                "tenant_id": "tenant_xyz789", 
                "name": "CallWaiting.ai Development",
                "permissions": ["synthesize", "voices"],
                "rate_limit": {
                    "requests_per_minute": 100,
                    "requests_per_hour": 1000
                },
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
        }
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key and return tenant info.
        Priority: Supabase (if configured) -> in-memory demo keys.
        """
        # Try Supabase-backed auth first
        tenant = supabase_auth.get_tenant_by_api_key(api_key)
        if tenant:
            # Ensure api_key included for downstream permission checks
            tenant.setdefault("api_key", api_key)
            return tenant

        # Fallback to in-memory keys
        if api_key not in self.api_keys:
            return None

        key_info = self.api_keys[api_key]
        if not key_info.get("is_active", False):
            return None

        # Ensure shape is consistent with Supabase return
        key_info = {
            **key_info,
            "api_key": api_key,
            "permissions": key_info.get("permissions", ["synthesize", "voices"]),
            "rate_limit": key_info.get("rate_limit", {"requests_per_minute": 1000, "requests_per_hour": 10000}),
        }
        return key_info
    
    def check_permission(self, api_key: str, permission: str) -> bool:
        """Check if API key has specific permission"""
        key_info = self.validate_api_key(api_key)
        if not key_info:
            return False
        
        return permission in key_info.get("permissions", [])

class RateLimiter:
    """Advanced rate limiting with Redis backend"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def check_rate_limit(
        self, 
        api_key: str, 
        limit_type: str = "requests_per_minute"
    ) -> Dict[str, Any]:
        """Check rate limit for API key"""
        key_info = APIKeyManager().validate_api_key(api_key)
        if not key_info:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        rate_limit = key_info.get("rate_limit", {})
        limit = rate_limit.get(limit_type, 1000)
        
        # Create rate limit key
        current_time = int(time.time())
        if limit_type == "requests_per_minute":
            window = current_time // 60
            key = f"rate_limit:{api_key}:minute:{window}"
            window_duration = 60
        else:  # requests_per_hour
            window = current_time // 3600
            key = f"rate_limit:{api_key}:hour:{window}"
            window_duration = 3600
        
        # Check current count
        current_count = self.redis.get(key)
        if current_count is None:
            current_count = 0
        else:
            current_count = int(current_count)
        
        if current_count >= limit:
            return {
                "allowed": False,
                "limit": limit,
                "current": current_count,
                "reset_time": (window + 1) * window_duration
            }
        
        # Increment counter
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_duration)
        pipe.execute()
        
        return {
            "allowed": True,
            "limit": limit,
            "current": current_count + 1,
            "reset_time": (window + 1) * window_duration
        }

# Global instances
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter(redis_client)

# FastAPI dependencies
security = HTTPBearer()

async def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """FastAPI dependency to get current tenant from API key"""
    api_key = credentials.credentials
    
    key_info = api_key_manager.validate_api_key(api_key)
    if not key_info:
        raise HTTPException(
            status_code=401, 
            detail="Invalid or inactive API key"
        )
    
    return key_info

async def check_rate_limit_dependency(
    request: Request,
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
) -> Dict[str, Any]:
    """FastAPI dependency for rate limiting"""
    api_key = request.headers.get("authorization", "").replace("Bearer ", "")
    
    rate_limit_result = await rate_limiter.check_rate_limit(api_key)
    if not rate_limit_result["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Limit: {rate_limit_result['limit']}, "
                   f"Current: {rate_limit_result['current']}, "
                   f"Reset at: {rate_limit_result['reset_time']}"
        )
    
    return rate_limit_result

async def require_permission(
    permission: str,
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
) -> Dict[str, Any]:
    """FastAPI dependency to check specific permissions"""
    api_key = tenant_info.get("api_key", "")
    
    if not api_key_manager.check_permission(api_key, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Permission '{permission}' required"
        )
    
    return tenant_info

# Rate limiting decorators
def rate_limit(limit_type: str = "requests_per_minute"):
    """Decorator for rate limiting endpoints"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract API key from request
            request = kwargs.get('request')
            if request:
                api_key = request.headers.get("authorization", "").replace("Bearer ", "")
                rate_limit_result = await rate_limiter.check_rate_limit(api_key, limit_type)
                if not rate_limit_result["allowed"]:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded"
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
