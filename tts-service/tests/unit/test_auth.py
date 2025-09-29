"""
Unit tests for authentication and authorization
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import time

from src.api.auth import APIKeyManager, RateLimiter, get_current_tenant, check_rate_limit_dependency


class TestAPIKeyManager:
    """Test cases for API key management"""
    
    @pytest.fixture
    def api_key_manager(self):
        """Create API key manager instance"""
        return APIKeyManager()
    
    def test_validate_valid_api_key(self, api_key_manager):
        """Test validation of valid API key"""
        api_key = "sk_test_1234567890abcdef"
        result = api_key_manager.validate_api_key(api_key)
        
        assert result is not None
        assert result["tenant_id"] == "tenant_abc123"
        assert result["name"] == "CallWaiting.ai Production"
        assert "synthesize" in result["permissions"]
    
    def test_validate_invalid_api_key(self, api_key_manager):
        """Test validation of invalid API key"""
        result = api_key_manager.validate_api_key("invalid_key")
        assert result is None
    
    def test_validate_inactive_api_key(self, api_key_manager):
        """Test validation of inactive API key"""
        # Make a key inactive
        api_key = "sk_test_1234567890abcdef"
        api_key_manager.api_keys[api_key]["is_active"] = False
        
        result = api_key_manager.validate_api_key(api_key)
        assert result is None
    
    def test_check_permission_valid(self, api_key_manager):
        """Test permission check with valid permission"""
        api_key = "sk_test_1234567890abcdef"
        result = api_key_manager.check_permission(api_key, "synthesize")
        assert result is True
    
    def test_check_permission_invalid(self, api_key_manager):
        """Test permission check with invalid permission"""
        api_key = "sk_test_1234567890abcdef"
        result = api_key_manager.check_permission(api_key, "admin")
        assert result is False
    
    def test_check_permission_invalid_key(self, api_key_manager):
        """Test permission check with invalid API key"""
        result = api_key_manager.check_permission("invalid_key", "synthesize")
        assert result is False


class TestRateLimiter:
    """Test cases for rate limiting"""
    
    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.pipeline.return_value = Mock()
        return mock_redis
    
    @pytest.fixture
    def rate_limiter(self, mock_redis):
        """Create rate limiter with mock Redis"""
        return RateLimiter(mock_redis)
    
    @pytest.mark.asyncio
    async def test_rate_limit_allowed(self, rate_limiter, mock_redis):
        """Test rate limit check when allowed"""
        # Mock pipeline
        mock_pipeline = Mock()
        mock_pipeline.incr.return_value = None
        mock_pipeline.expire.return_value = None
        mock_pipeline.execute.return_value = [1, True]
        mock_redis.pipeline.return_value = mock_pipeline
        
        result = await rate_limiter.check_rate_limit("sk_test_1234567890abcdef")
        
        assert result["allowed"] is True
        assert result["current"] == 1
        assert result["limit"] == 1000
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, rate_limiter, mock_redis):
        """Test rate limit check when exceeded"""
        # Mock Redis to return count at limit
        mock_redis.get.return_value = "1000"
        
        result = await rate_limiter.check_rate_limit("sk_test_1234567890abcdef")
        
        assert result["allowed"] is False
        assert result["current"] == 1000
        assert result["limit"] == 1000
    
    @pytest.mark.asyncio
    async def test_rate_limit_invalid_key(self, rate_limiter):
        """Test rate limit check with invalid API key"""
        with pytest.raises(Exception, match="Invalid API key"):
            await rate_limiter.check_rate_limit("invalid_key")
    
    @pytest.mark.asyncio
    async def test_rate_limit_hourly(self, rate_limiter, mock_redis):
        """Test hourly rate limit"""
        mock_pipeline = Mock()
        mock_pipeline.incr.return_value = None
        mock_pipeline.expire.return_value = None
        mock_pipeline.execute.return_value = [1, True]
        mock_redis.pipeline.return_value = mock_pipeline
        
        result = await rate_limiter.check_rate_limit(
            "sk_test_1234567890abcdef", 
            "requests_per_hour"
        )
        
        assert result["allowed"] is True
        assert result["limit"] == 10000  # Hourly limit


class TestAuthDependencies:
    """Test cases for FastAPI authentication dependencies"""
    
    @pytest.fixture
    def mock_credentials(self):
        """Create mock HTTP credentials"""
        credentials = Mock()
        credentials.credentials = "sk_test_1234567890abcdef"
        return credentials
    
    @pytest.mark.asyncio
    async def test_get_current_tenant_success(self, mock_credentials):
        """Test successful tenant retrieval"""
        result = await get_current_tenant(mock_credentials)
        
        assert result["tenant_id"] == "tenant_abc123"
        assert result["name"] == "CallWaiting.ai Production"
    
    @pytest.mark.asyncio
    async def test_get_current_tenant_invalid_key(self, mock_credentials):
        """Test tenant retrieval with invalid key"""
        mock_credentials.credentials = "invalid_key"
        
        with pytest.raises(Exception, match="Invalid or inactive API key"):
            await get_current_tenant(mock_credentials)
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_dependency_success(self, mock_credentials):
        """Test successful rate limit check"""
        mock_request = Mock()
        mock_request.headers = {"authorization": "Bearer sk_test_1234567890abcdef"}
        
        with patch('src.api.auth.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit.return_value = {
                "allowed": True,
                "limit": 1000,
                "current": 1,
                "reset_time": time.time() + 60
            }
            
            result = await check_rate_limit_dependency(mock_request, {"tenant_id": "test"})
            
            assert result["allowed"] is True
    
    @pytest.mark.asyncio
    async def test_check_rate_limit_dependency_exceeded(self, mock_credentials):
        """Test rate limit exceeded"""
        mock_request = Mock()
        mock_request.headers = {"authorization": "Bearer sk_test_1234567890abcdef"}
        
        with patch('src.api.auth.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit.return_value = {
                "allowed": False,
                "limit": 1000,
                "current": 1000,
                "reset_time": time.time() + 60
            }
            
            with pytest.raises(Exception, match="Rate limit exceeded"):
                await check_rate_limit_dependency(mock_request, {"tenant_id": "test"})
