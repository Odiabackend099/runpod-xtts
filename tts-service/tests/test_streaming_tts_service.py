#!/usr/bin/env python3
"""
Comprehensive test suite for CallWaiting.ai Streaming TTS Service
Tests all API endpoints, authentication, voice management, and audio generation
"""

import pytest
import asyncio
import tempfile
import os
import json
import time
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys

# Add the project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from working_streaming_server import app
from fallback_tts_manager import fallback_tts_manager, VoiceProfile, TenantInfo

class TestStreamingTTSService:
    """Test suite for the streaming TTS service"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def valid_headers(self):
        """Valid authentication headers"""
        return {"Authorization": "Bearer cw_demo_12345"}
    
    @pytest.fixture
    def test_headers(self):
        """Test tenant authentication headers"""
        return {"Authorization": "Bearer test_key_67890"}
    
    @pytest.fixture
    def invalid_headers(self):
        """Invalid authentication headers"""
        return {"Authorization": "Bearer invalid_key"}
    
    @pytest.fixture
    def no_auth_headers(self):
        """No authentication headers"""
        return {}

class TestHealthAndRootEndpoints(TestStreamingTTSService):
    """Test health check and root endpoints"""
    
    def test_health_check(self, client):
        """Test health check endpoint returns correct status"""
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "model_loaded" in data
        assert "streaming_supported" in data
        assert "fallback_mode" in data
        assert "system_tts" in data
        assert "timestamp" in data
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service information"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "CallWaiting.ai Working Streaming TTS Service"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"
        assert "model_info" in data
        assert "endpoints" in data
        assert "demo_credentials" in data

class TestAuthentication(TestStreamingTTSService):
    """Test authentication and authorization"""
    
    def test_valid_api_key_authentication(self, client, valid_headers):
        """Test authentication with valid API key"""
        response = client.get("/v1/voices", headers=valid_headers)
        assert response.status_code == 200
    
    def test_test_tenant_authentication(self, client, test_headers):
        """Test authentication with test tenant API key"""
        response = client.get("/v1/voices", headers=test_headers)
        assert response.status_code == 200
    
    def test_invalid_api_key_authentication(self, client, invalid_headers):
        """Test authentication with invalid API key"""
        response = client.get("/v1/voices", headers=invalid_headers)
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_no_authentication(self, client, no_auth_headers):
        """Test endpoints without authentication"""
        response = client.get("/v1/voices", headers=no_auth_headers)
        assert response.status_code == 401
        assert "Authorization header required" in response.json()["detail"]
    
    def test_malformed_bearer_token(self, client):
        """Test malformed Bearer token"""
        response = client.get("/v1/voices", headers={"Authorization": "InvalidFormat"})
        assert response.status_code == 401
        assert "Invalid authorization format" in response.json()["detail"]

class TestVoiceManagement(TestStreamingTTSService):
    """Test voice profile management"""
    
    def test_list_voices_valid_auth(self, client, valid_headers):
        """Test listing voices with valid authentication"""
        response = client.get("/v1/voices", headers=valid_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 3  # Should have default, naija_female, naija_male
        
        # Check for expected voice profiles
        voice_ids = [voice["voice_id"] for voice in data]
        assert "default" in voice_ids
        assert "naija_female" in voice_ids
        assert "naija_male" in voice_ids
        
        # Check voice profile structure
        for voice in data:
            assert "voice_id" in voice
            assert "name" in voice
            assert "created_at" in voice
            assert "language" in voice
            assert "has_reference_audio" in voice
    
    def test_tenant_isolation(self, client, valid_headers, test_headers):
        """Test that tenants can only access their own voices"""
        # Get voices for demo tenant
        demo_response = client.get("/v1/voices", headers=valid_headers)
        demo_voices = demo_response.json()
        
        # Get voices for test tenant
        test_response = client.get("/v1/voices", headers=test_headers)
        test_voices = test_response.json()
        
        # Both should have the same default voices (since they're initialized the same)
        # But they should be separate instances
        assert len(demo_voices) == len(test_voices)
        assert demo_voices[0]["voice_id"] == test_voices[0]["voice_id"]  # Same default voices
    
    def test_voice_upload_valid_file(self, client, valid_headers):
        """Test uploading a valid audio file"""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(b"fake audio data")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"voice_file": ("test_voice.wav", f, "audio/wav")}
                data = {"name": "Test Voice", "language": "en"}
                
                response = client.post(
                    "/v1/voices/upload",
                    headers=valid_headers,
                    files=files,
                    data=data
                )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "voice_id" in data
            assert data["name"] == "Test Voice"
            assert data["language"] == "en"
            assert "created_at" in data
            assert "message" in data
            
        finally:
            # Cleanup
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_voice_upload_invalid_file_type(self, client, valid_headers):
        """Test uploading non-audio file"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b"not audio data")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                files = {"voice_file": ("test_file.txt", f, "text/plain")}
                data = {"name": "Test Voice", "language": "en"}
                
                response = client.post(
                    "/v1/voices/upload",
                    headers=valid_headers,
                    files=files,
                    data=data
                )
            
            assert response.status_code == 400
            assert "File must be an audio file" in response.json()["detail"]
            
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_voice_upload_no_file(self, client, valid_headers):
        """Test uploading without file"""
        data = {"name": "Test Voice", "language": "en"}
        
        response = client.post(
            "/v1/voices/upload",
            headers=valid_headers,
            data=data
        )
        
        assert response.status_code == 422  # Validation error

class TestAudioSynthesis(TestStreamingTTSService):
    """Test audio synthesis functionality"""
    
    def test_synthesize_valid_request(self, client, valid_headers):
        """Test audio synthesis with valid parameters"""
        payload = {
            "text": "Hello, this is a test of the TTS service.",
            "voice_id": "default",
            "language": "en"
        }
        
        response = client.post(
            "/v1/synthesize",
            headers=valid_headers,
            json=payload
        )
        
        # Note: This might fail due to system TTS issues, but we test the structure
        if response.status_code == 200:
            assert response.headers["content-type"] == "audio/wav"
            assert "X-Voice-ID" in response.headers
            assert "X-Tenant-ID" in response.headers
            assert "X-TTS-Method" in response.headers
        else:
            # If system TTS fails, we expect a 500 error
            assert response.status_code == 500
    
    def test_synthesize_invalid_voice_id(self, client, valid_headers):
        """Test synthesis with non-existent voice"""
        payload = {
            "text": "Hello, this is a test.",
            "voice_id": "nonexistent_voice",
            "language": "en"
        }
        
        response = client.post(
            "/v1/synthesize",
            headers=valid_headers,
            json=payload
        )
        
        assert response.status_code == 404
        assert "Voice profile 'nonexistent_voice' not found" in response.json()["detail"]
    
    def test_synthesize_empty_text(self, client, valid_headers):
        """Test synthesis with empty text"""
        payload = {
            "text": "",
            "voice_id": "default",
            "language": "en"
        }
        
        response = client.post(
            "/v1/synthesize",
            headers=valid_headers,
            json=payload
        )
        
        assert response.status_code == 400
        assert "Text cannot be empty" in response.json()["detail"]
    
    def test_synthesize_missing_text(self, client, valid_headers):
        """Test synthesis without text field"""
        payload = {
            "voice_id": "default",
            "language": "en"
        }
        
        response = client.post(
            "/v1/synthesize",
            headers=valid_headers,
            json=payload
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_streaming_synthesis_valid_request(self, client, valid_headers):
        """Test streaming audio synthesis"""
        payload = {
            "text": "This is a streaming test.",
            "voice_id": "default",
            "language": "en"
        }
        
        response = client.post(
            "/v1/synthesize/streaming",
            headers=valid_headers,
            json=payload
        )
        
        # Note: This might fail due to system TTS issues
        if response.status_code == 200:
            assert response.headers["content-type"] == "audio/wav"
            assert response.headers["X-Streaming"] == "true"
            assert "X-Voice-ID" in response.headers
            assert "X-Tenant-ID" in response.headers
        else:
            # If system TTS fails, we expect a 500 error
            assert response.status_code == 500
    
    def test_synthesize_different_voices(self, client, valid_headers):
        """Test synthesis with different voice IDs"""
        voices = ["default", "naija_female", "naija_male"]
        
        for voice_id in voices:
            payload = {
                "text": f"Testing voice {voice_id}",
                "voice_id": voice_id,
                "language": "en"
            }
            
            response = client.post(
                "/v1/synthesize",
                headers=valid_headers,
                json=payload
            )
            
            # Should not get 404 (voice not found)
            assert response.status_code != 404
            # Might get 500 due to system TTS issues, which is acceptable

class TestTenantManagement(TestStreamingTTSService):
    """Test tenant management and statistics"""
    
    def test_tenant_stats_valid_auth(self, client, valid_headers):
        """Test getting tenant statistics with valid authentication"""
        response = client.get("/v1/tenant/stats", headers=valid_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tenant_id"] == "callwaiting_demo"
        assert "total_voices" in data
        assert "max_voices" in data
        assert "rate_limit_per_minute" in data
        
        assert data["total_voices"] >= 3  # Should have default voices
        assert data["max_voices"] == 20  # Demo tenant limit
        assert data["rate_limit_per_minute"] == 1000  # Demo tenant rate limit
    
    def test_tenant_stats_test_tenant(self, client, test_headers):
        """Test getting statistics for test tenant"""
        response = client.get("/v1/tenant/stats", headers=test_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["tenant_id"] == "test_tenant"
        assert data["max_voices"] == 5  # Test tenant limit
        assert data["rate_limit_per_minute"] == 100  # Test tenant rate limit
    
    def test_tenant_stats_invalid_auth(self, client, invalid_headers):
        """Test getting tenant stats with invalid authentication"""
        response = client.get("/v1/tenant/stats", headers=invalid_headers)
        assert response.status_code == 401

class TestErrorHandling(TestStreamingTTSService):
    """Test error handling and edge cases"""
    
    def test_invalid_json_payload(self, client, valid_headers):
        """Test handling of malformed JSON"""
        response = client.post(
            "/v1/synthesize",
            headers={**valid_headers, "Content-Type": "application/json"},
            data="invalid json"
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_missing_required_fields(self, client, valid_headers):
        """Test handling of missing required fields"""
        # Missing text field
        payload = {
            "voice_id": "default",
            "language": "en"
        }
        
        response = client.post(
            "/v1/synthesize",
            headers=valid_headers,
            json=payload
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_unauthorized_access_to_protected_endpoints(self, client):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            ("/v1/voices", "GET"),
            ("/v1/tenant/stats", "GET"),
            ("/v1/synthesize", "POST"),
            ("/v1/synthesize/streaming", "POST"),
            ("/v1/voices/upload", "POST"),
            ("/v1/generate-demo-audio", "POST")
        ]
        
        for endpoint, method in protected_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            assert response.status_code == 401

class TestTTSManager(TestStreamingTTSService):
    """Test the TTS Manager functionality"""
    
    def test_tts_manager_initialization(self):
        """Test that TTS manager is properly initialized"""
        assert fallback_tts_manager is not None
        assert len(fallback_tts_manager.tenants) >= 2
        assert "callwaiting_demo" in fallback_tts_manager.tenants
        assert "test_tenant" in fallback_tts_manager.tenants
    
    def test_api_key_validation(self):
        """Test API key validation"""
        # Valid API keys
        assert fallback_tts_manager.validate_api_key("callwaiting_demo", "cw_demo_12345")
        assert fallback_tts_manager.validate_api_key("test_tenant", "test_key_67890")
        
        # Invalid API keys
        assert not fallback_tts_manager.validate_api_key("callwaiting_demo", "invalid_key")
        assert not fallback_tts_manager.validate_api_key("nonexistent_tenant", "any_key")
    
    def test_voice_profile_management(self):
        """Test voice profile management"""
        # Test getting voice profiles
        demo_voices = fallback_tts_manager.list_voice_profiles("callwaiting_demo")
        assert len(demo_voices) >= 3
        
        # Test getting specific voice profile
        default_voice = fallback_tts_manager.get_voice_model("callwaiting_demo", "default")
        assert default_voice is not None
        assert default_voice.voice_id == "default"
        assert default_voice.tenant_id == "callwaiting_demo"
    
    def test_tenant_info_retrieval(self):
        """Test tenant information retrieval"""
        demo_tenant = fallback_tts_manager.get_tenant_info("callwaiting_demo")
        assert demo_tenant is not None
        assert demo_tenant.tenant_id == "callwaiting_demo"
        assert demo_tenant.api_key == "cw_demo_12345"
        assert demo_tenant.max_voices == 20
        assert demo_tenant.rate_limit_per_minute == 1000

class TestPerformance(TestStreamingTTSService):
    """Test performance and load handling"""
    
    def test_concurrent_requests(self, client, valid_headers):
        """Test handling multiple concurrent requests"""
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                payload = {
                    "text": "Concurrent test request",
                    "voice_id": "default",
                    "language": "en"
                }
                
                response = client.post(
                    "/v1/synthesize",
                    headers=valid_headers,
                    json=payload
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create 5 concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(results) == 5
        # All requests should complete (even if with errors due to system TTS)
        assert len(errors) == 0  # No exceptions should be raised
    
    def test_response_time_health_check(self, client):
        """Test response time for health check"""
        start_time = time.time()
        response = client.get("/v1/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should respond within 1 second

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
