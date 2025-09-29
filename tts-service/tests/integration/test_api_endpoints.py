"""
Integration tests for API endpoints
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from src.api.endpoints import app


class TestAPIEndpoints:
    """Integration tests for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_tts_model(self):
        """Mock TTS model"""
        with patch('src.api.endpoints.tts_model') as mock:
            mock.initialize = AsyncMock()
            mock.get_model_info.return_value = {
                "model_name": "test_model",
                "device": "cpu",
                "sample_rate": 24000,
                "available": True,
                "initialized": True
            }
            mock.synthesize_streaming = AsyncMock()
            mock.synthesize_streaming.return_value = [b'audio_chunk_1', b'audio_chunk_2']
            mock.synthesize_batch = AsyncMock()
            mock.synthesize_batch.return_value = b'complete_audio_data'
            yield mock
    
    @pytest.fixture
    def mock_voice_manager(self):
        """Mock voice manager"""
        with patch('src.api.endpoints.voice_manager') as mock:
            mock.get_voice_config = AsyncMock()
            mock.get_voice_config.return_value = {
                "voice_id": "test_voice",
                "language": "en",
                "reference_audio_path": None,
                "is_preloaded": True
            }
            mock.get_tenant_voices = AsyncMock()
            mock.get_tenant_voices.return_value = [
                {
                    "voice_id": "test_voice",
                    "name": "Test Voice",
                    "description": "Test voice description",
                    "language": "en",
                    "is_preloaded": True
                }
            ]
            mock.create_voice_profile = AsyncMock()
            mock.create_voice_profile.return_value = {
                "voice_id": "new_voice",
                "name": "New Voice",
                "description": "New voice description",
                "language": "en",
                "created_at": "2024-01-01T00:00:00"
            }
            mock.delete_voice_profile = AsyncMock()
            mock.delete_voice_profile.return_value = True
            mock.get_tenant_stats = AsyncMock()
            mock.get_tenant_stats.return_value = {
                "tenant_id": "test_tenant",
                "custom_voices": 1,
                "preloaded_voices": 3,
                "total_voices": 4
            }
            yield mock
    
    @pytest.fixture
    def mock_metrics(self):
        """Mock metrics collector"""
        with patch('src.api.endpoints.metrics') as mock:
            mock.start_time = 1000.0
            mock.get_memory_usage.return_value = {
                'current': {'used_percent': 50.0},
                'average_used_percent': 45.0,
                'peak_used_percent': 60.0
            }
            mock.get_system_metrics.return_value = {
                'uptime': 3600,
                'memory': {'current': {'used_percent': 50.0}},
                'cpu': {'current': {'percent': 25.0}},
                'requests': {'total_requests': 100, 'error_rate': 0.01},
                'tenants': {'total_tenants': 5, 'active_tenants': 3}
            }
            mock.get_tenant_metrics.return_value = {
                'requests': 10,
                'errors': 0,
                'error_rate': 0.0,
                'average_latency': 1.5,
                'p95_latency': 2.0
            }
            yield mock
    
    @pytest.fixture
    def mock_auth(self):
        """Mock authentication"""
        with patch('src.api.endpoints.get_current_tenant') as mock:
            mock.return_value = {
                "tenant_id": "test_tenant",
                "name": "Test Tenant",
                "permissions": ["synthesize", "voices", "upload"],
                "rate_limit": {
                    "requests_per_minute": 1000,
                    "requests_per_hour": 10000
                }
            }
            yield mock
    
    @pytest.fixture
    def mock_rate_limit(self):
        """Mock rate limiting"""
        with patch('src.api.endpoints.check_rate_limit_dependency') as mock:
            mock.return_value = {
                "allowed": True,
                "limit": 1000,
                "current": 1,
                "reset_time": 1000
            }
            yield mock
    
    def test_health_check(self, client, mock_tts_model, mock_metrics):
        """Test health check endpoint"""
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "model" in data
        assert "uptime" in data
        assert "memory_usage" in data
    
    def test_health_check_degraded(self, client, mock_tts_model, mock_metrics):
        """Test health check when model is not initialized"""
        mock_tts_model.get_model_info.return_value = {
            "model_name": "test_model",
            "device": "cpu",
            "sample_rate": 24000,
            "available": True,
            "initialized": False
        }
        
        response = client.get("/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
    
    def test_synthesize_streaming(self, client, mock_tts_model, mock_voice_manager, mock_auth, mock_rate_limit):
        """Test streaming synthesis endpoint"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        data = {
            "text": "Hello world",
            "voice_id": "test_voice",
            "language": "en",
            "streaming": "true"
        }
        
        response = client.post("/v1/synthesize", headers=headers, data=data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert response.headers["X-Tenant-ID"] == "test_tenant"
        assert response.headers["X-Voice-ID"] == "test_voice"
        assert response.headers["X-Streaming"] == "true"
        
        # Check that streaming was called
        mock_tts_model.synthesize_streaming.assert_called_once()
    
    def test_synthesize_batch(self, client, mock_tts_model, mock_voice_manager, mock_auth, mock_rate_limit):
        """Test batch synthesis endpoint"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        data = {
            "text": "Hello world",
            "voice_id": "test_voice",
            "language": "en",
            "streaming": "false"
        }
        
        response = client.post("/v1/synthesize", headers=headers, data=data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "audio/wav"
        assert response.headers["X-Streaming"] == "false"
        
        # Check that batch synthesis was called
        mock_tts_model.synthesize_batch.assert_called_once()
    
    def test_synthesize_with_ssml(self, client, mock_tts_model, mock_voice_manager, mock_auth, mock_rate_limit):
        """Test synthesis with SSML"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        data = {
            "text": "Hello world",
            "voice_id": "test_voice",
            "ssml": "<speak><break time='0.5s'/>Hello world</speak>",
            "streaming": "true"
        }
        
        response = client.post("/v1/synthesize", headers=headers, data=data)
        
        assert response.status_code == 200
        mock_tts_model.synthesize_streaming.assert_called_once()
    
    def test_synthesize_voice_not_found(self, client, mock_tts_model, mock_voice_manager, mock_auth, mock_rate_limit):
        """Test synthesis with non-existent voice"""
        mock_voice_manager.get_voice_config.return_value = None
        
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        data = {
            "text": "Hello world",
            "voice_id": "nonexistent_voice"
        }
        
        response = client.post("/v1/synthesize", headers=headers, data=data)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()
    
    def test_synthesize_unauthorized(self, client):
        """Test synthesis without authentication"""
        data = {
            "text": "Hello world",
            "voice_id": "test_voice"
        }
        
        response = client.post("/v1/synthesize", data=data)
        
        assert response.status_code == 401
    
    def test_get_voices(self, client, mock_voice_manager, mock_auth):
        """Test get voices endpoint"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        response = client.get("/v1/voices", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test_tenant"
        assert "voices" in data
        assert "total_count" in data
        assert len(data["voices"]) == 1
        assert data["voices"][0]["voice_id"] == "test_voice"
    
    def test_upload_voice(self, client, mock_voice_manager, mock_auth):
        """Test voice upload endpoint"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(b'fake_audio_data')
            temp_path = temp_file.name
        
        try:
            with open(temp_path, 'rb') as audio_file:
                files = {"audio_file": ("test.wav", audio_file, "audio/wav")}
                data = {
                    "voice_id": "new_voice",
                    "name": "New Voice",
                    "description": "New voice description",
                    "language": "en"
                }
                
                response = client.post("/v1/voices/upload", headers=headers, data=data, files=files)
                
                assert response.status_code == 200
                response_data = response.json()
                assert "message" in response_data
                assert "voice_profile" in response_data
                assert response_data["voice_profile"]["voice_id"] == "new_voice"
                
                mock_voice_manager.create_voice_profile.assert_called_once()
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_upload_voice_invalid_file(self, client, mock_voice_manager, mock_auth):
        """Test voice upload with invalid file type"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        # Create temporary text file (not audio)
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as temp_file:
            temp_file.write(b'not_audio_data')
            temp_path = temp_file.name
        
        try:
            with open(temp_path, 'rb') as text_file:
                files = {"audio_file": ("test.txt", text_file, "text/plain")}
                data = {
                    "voice_id": "new_voice",
                    "name": "New Voice",
                    "language": "en"
                }
                
                response = client.post("/v1/voices/upload", headers=headers, data=data, files=files)
                
                assert response.status_code == 400
                assert "audio file" in response.json()["error"]["message"].lower()
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_delete_voice(self, client, mock_voice_manager, mock_auth):
        """Test voice deletion endpoint"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        response = client.delete("/v1/voices/test_voice", headers=headers)
        
        assert response.status_code == 200
        response_data = response.json()
        assert "deleted successfully" in response_data["message"]
        
        mock_voice_manager.delete_voice_profile.assert_called_once_with("test_tenant", "test_voice")
    
    def test_delete_voice_not_found(self, client, mock_voice_manager, mock_auth):
        """Test voice deletion with non-existent voice"""
        mock_voice_manager.delete_voice_profile.return_value = False
        
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        response = client.delete("/v1/voices/nonexistent_voice", headers=headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"]["message"].lower()
    
    def test_get_tenant_stats(self, client, mock_voice_manager, mock_metrics, mock_auth):
        """Test tenant statistics endpoint"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        response = client.get("/v1/tenant/stats", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "test_tenant"
        assert "voice_stats" in data
        assert "usage_stats" in data
        assert data["voice_stats"]["total_voices"] == 4
    
    def test_get_metrics_admin(self, client, mock_tts_model, mock_metrics, mock_auth):
        """Test metrics endpoint (admin only)"""
        # Mock admin permissions
        with patch('src.api.endpoints.require_permission') as mock_permission:
            mock_permission.return_value = {
                "tenant_id": "admin_tenant",
                "permissions": ["admin"]
            }
            
            headers = {"Authorization": "Bearer sk_admin_1234567890abcdef"}
            
            response = client.get("/v1/metrics", headers=headers)
            
            assert response.status_code == 200
            data = response.json()
            assert "system_metrics" in data
            assert "model_info" in data
            assert "streaming_status" in data
    
    def test_get_metrics_unauthorized(self, client, mock_auth):
        """Test metrics endpoint without admin permissions"""
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        
        response = client.get("/v1/metrics", headers=headers)
        
        assert response.status_code == 403
    
    def test_synthesis_error_handling(self, client, mock_tts_model, mock_voice_manager, mock_auth, mock_rate_limit):
        """Test error handling in synthesis"""
        mock_tts_model.synthesize_streaming.side_effect = Exception("Synthesis failed")
        
        headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
        data = {
            "text": "Hello world",
            "voice_id": "test_voice"
        }
        
        response = client.post("/v1/synthesize", headers=headers, data=data)
        
        assert response.status_code == 500
        assert "Internal server error" in response.json()["error"]["message"]
    
    def test_rate_limit_exceeded(self, client, mock_tts_model, mock_voice_manager, mock_auth):
        """Test rate limit exceeded"""
        with patch('src.api.endpoints.check_rate_limit_dependency') as mock_rate_limit:
            mock_rate_limit.side_effect = Exception("Rate limit exceeded")
            
            headers = {"Authorization": "Bearer sk_test_1234567890abcdef"}
            data = {
                "text": "Hello world",
                "voice_id": "test_voice"
            }
            
            response = client.post("/v1/synthesize", headers=headers, data=data)
            
            assert response.status_code == 429
