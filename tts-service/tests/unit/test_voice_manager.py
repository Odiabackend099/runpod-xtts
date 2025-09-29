"""
Unit tests for voice management system
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from src.tenancy.voice_manager import VoiceManager, VoiceProfile


class TestVoiceManager:
    """Test cases for voice management"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
            temp_path = temp_file.name
        
        yield f"sqlite:///{temp_path}"
        
        # Cleanup
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def voice_manager(self, temp_db, temp_storage):
        """Create voice manager instance"""
        return VoiceManager(db_url=temp_db, storage_path=temp_storage)
    
    def test_load_preloaded_voices(self, voice_manager):
        """Test loading preloaded voices"""
        voices = voice_manager.preloaded_voices
        
        assert "naija_female" in voices
        assert "naija_male" in voices
        assert "default" in voices
        
        assert voices["naija_female"]["name"] == "Nigerian Female"
        assert voices["naija_female"]["language"] == "en"
        assert voices["naija_female"]["is_preloaded"] is True
    
    @pytest.mark.asyncio
    async def test_get_tenant_voices(self, voice_manager):
        """Test getting voices for a tenant"""
        tenant_id = "test_tenant"
        voices = await voice_manager.get_tenant_voices(tenant_id)
        
        # Should include preloaded voices
        assert len(voices) >= 3  # At least 3 preloaded voices
        
        # Check structure
        for voice in voices:
            assert "voice_id" in voice
            assert "name" in voice
            assert "description" in voice
            assert "language" in voice
        
        # Check specific preloaded voices
        voice_ids = [v["voice_id"] for v in voices]
        assert "naija_female" in voice_ids
        assert "naija_male" in voice_ids
        assert "default" in voice_ids
    
    @pytest.mark.asyncio
    async def test_create_voice_profile(self, voice_manager):
        """Test creating a voice profile"""
        tenant_id = "test_tenant"
        voice_id = "custom_voice"
        name = "Custom Voice"
        description = "A custom voice profile"
        language = "en"
        
        # Mock audio data
        audio_data = b"fake_audio_data"
        
        with patch.object(voice_manager, '_store_reference_audio') as mock_store:
            mock_store.return_value = "/path/to/stored/audio.wav"
            
            result = await voice_manager.create_voice_profile(
                tenant_id=tenant_id,
                voice_id=voice_id,
                name=name,
                description=description,
                language=language,
                reference_audio_data=audio_data
            )
            
            assert result["voice_id"] == voice_id
            assert result["name"] == name
            assert result["description"] == description
            assert result["language"] == language
            assert result["reference_audio_path"] == "/path/to/stored/audio.wav"
            
            mock_store.assert_called_once_with(tenant_id, voice_id, audio_data)
    
    @pytest.mark.asyncio
    async def test_create_voice_profile_duplicate(self, voice_manager):
        """Test creating duplicate voice profile"""
        tenant_id = "test_tenant"
        voice_id = "duplicate_voice"
        
        # Create first voice
        await voice_manager.create_voice_profile(
            tenant_id=tenant_id,
            voice_id=voice_id,
            name="First Voice"
        )
        
        # Try to create duplicate
        with pytest.raises(ValueError, match="already exists"):
            await voice_manager.create_voice_profile(
                tenant_id=tenant_id,
                voice_id=voice_id,
                name="Second Voice"
            )
    
    @pytest.mark.asyncio
    async def test_store_reference_audio(self, voice_manager):
        """Test storing reference audio"""
        tenant_id = "test_tenant"
        voice_id = "test_voice"
        audio_data = b"fake_audio_data"
        
        result_path = await voice_manager._store_reference_audio(
            tenant_id, voice_id, audio_data
        )
        
        # Check that file was created
        assert os.path.exists(result_path)
        
        # Check that content matches
        with open(result_path, 'rb') as f:
            stored_data = f.read()
        assert stored_data == audio_data
        
        # Check path structure
        assert tenant_id in result_path
        assert voice_id in result_path
        assert result_path.endswith('.wav')
    
    @pytest.mark.asyncio
    async def test_get_voice_config_preloaded(self, voice_manager):
        """Test getting voice config for preloaded voice"""
        tenant_id = "test_tenant"
        voice_id = "naija_female"
        
        config = await voice_manager.get_voice_config(tenant_id, voice_id)
        
        assert config is not None
        assert config["voice_id"] == voice_id
        assert config["language"] == "en"
        assert config["reference_audio_path"] is None
        assert config["is_preloaded"] is True
    
    @pytest.mark.asyncio
    async def test_get_voice_config_custom(self, voice_manager):
        """Test getting voice config for custom voice"""
        tenant_id = "test_tenant"
        voice_id = "custom_voice"
        
        # Create custom voice
        await voice_manager.create_voice_profile(
            tenant_id=tenant_id,
            voice_id=voice_id,
            name="Custom Voice",
            reference_audio_data=b"fake_audio"
        )
        
        config = await voice_manager.get_voice_config(tenant_id, voice_id)
        
        assert config is not None
        assert config["voice_id"] == voice_id
        assert config["language"] == "en"
        assert config["is_custom"] is True
    
    @pytest.mark.asyncio
    async def test_get_voice_config_not_found(self, voice_manager):
        """Test getting voice config for non-existent voice"""
        tenant_id = "test_tenant"
        voice_id = "nonexistent_voice"
        
        config = await voice_manager.get_voice_config(tenant_id, voice_id)
        
        assert config is None
    
    @pytest.mark.asyncio
    async def test_delete_voice_profile(self, voice_manager):
        """Test deleting voice profile"""
        tenant_id = "test_tenant"
        voice_id = "voice_to_delete"
        
        # Create voice first
        await voice_manager.create_voice_profile(
            tenant_id=tenant_id,
            voice_id=voice_id,
            name="Voice to Delete"
        )
        
        # Delete voice
        result = await voice_manager.delete_voice_profile(tenant_id, voice_id)
        
        assert result is True
        
        # Verify voice is gone
        config = await voice_manager.get_voice_config(tenant_id, voice_id)
        assert config is None
    
    @pytest.mark.asyncio
    async def test_delete_voice_profile_not_found(self, voice_manager):
        """Test deleting non-existent voice profile"""
        tenant_id = "test_tenant"
        voice_id = "nonexistent_voice"
        
        result = await voice_manager.delete_voice_profile(tenant_id, voice_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_tenant_stats(self, voice_manager):
        """Test getting tenant statistics"""
        tenant_id = "test_tenant"
        
        # Create some custom voices
        await voice_manager.create_voice_profile(
            tenant_id=tenant_id,
            voice_id="voice1",
            name="Voice 1"
        )
        await voice_manager.create_voice_profile(
            tenant_id=tenant_id,
            voice_id="voice2",
            name="Voice 2"
        )
        
        stats = await voice_manager.get_tenant_stats(tenant_id)
        
        assert stats["tenant_id"] == tenant_id
        assert stats["custom_voices"] == 2
        assert stats["preloaded_voices"] == 3  # naija_female, naija_male, default
        assert stats["total_voices"] == 5
