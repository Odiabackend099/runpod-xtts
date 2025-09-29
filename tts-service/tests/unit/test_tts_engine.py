"""
Unit tests for Coqui XTTS model wrapper
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os

from src.models.coqui_xtts import CoquiXTTSModel


class TestCoquiXTTSModel:
    """Test cases for Coqui XTTS model wrapper"""
    
    @pytest.fixture
    def tts_model(self):
        """Create TTS model instance for testing"""
        return CoquiXTTSModel()
    
    @pytest.mark.asyncio
    async def test_initialization_success(self, tts_model):
        """Test successful model initialization"""
        with patch('src.models.coqui_xtts.TTS') as mock_tts:
            mock_tts_instance = Mock()
            mock_tts.return_value = mock_tts_instance
            
            result = await tts_model.initialize()
            
            assert result is True
            assert tts_model.model is not None
            mock_tts.assert_called_once_with(
                model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                progress_bar=False
            )
    
    @pytest.mark.asyncio
    async def test_initialization_failure(self, tts_model):
        """Test model initialization failure"""
        with patch('src.models.coqui_xtts.TTS') as mock_tts:
            mock_tts.side_effect = Exception("Model loading failed")
            
            with pytest.raises(Exception, match="Model loading failed"):
                await tts_model.initialize()
    
    @pytest.mark.asyncio
    async def test_synthesize_streaming_success(self, tts_model):
        """Test successful streaming synthesis"""
        # Mock the model
        tts_model.model = Mock()
        
        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            # Write minimal WAV header
            temp_file.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
        
        try:
            with patch('src.models.coqui_xtts.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = temp_path
                
                # Mock the streaming method
                with patch.object(tts_model, '_stream_audio_file') as mock_stream:
                    mock_stream.return_value = [b'audio_chunk_1', b'audio_chunk_2']
                    
                    chunks = []
                    async for chunk in tts_model.synthesize_streaming("Hello world"):
                        chunks.append(chunk)
                    
                    assert len(chunks) == 2
                    assert chunks[0] == b'audio_chunk_1'
                    assert chunks[1] == b'audio_chunk_2'
                    
                    # Verify model was called
                    tts_model.model.tts_to_file.assert_called_once()
        
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_synthesize_streaming_with_reference_audio(self, tts_model):
        """Test streaming synthesis with reference audio"""
        tts_model.model = Mock()
        
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            temp_file.write(b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00')
        
        try:
            with patch('src.models.coqui_xtts.tempfile.NamedTemporaryFile') as mock_temp:
                mock_temp.return_value.__enter__.return_value.name = temp_path
                
                with patch.object(tts_model, '_stream_audio_file') as mock_stream:
                    mock_stream.return_value = [b'audio_chunk']
                    
                    reference_audio = "/path/to/reference.wav"
                    chunks = []
                    async for chunk in tts_model.synthesize_streaming(
                        "Hello world", 
                        reference_audio=reference_audio
                    ):
                        chunks.append(chunk)
                    
                    # Verify model was called with reference audio
                    tts_model.model.tts_to_file.assert_called_once_with(
                        text="Hello world",
                        file_path=temp_path,
                        speaker_wav=reference_audio,
                        language="en"
                    )
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_synthesize_batch(self, tts_model):
        """Test batch synthesis"""
        tts_model.model = Mock()
        
        with patch.object(tts_model, 'synthesize_streaming') as mock_stream:
            mock_stream.return_value = [b'chunk1', b'chunk2', b'chunk3']
            
            result = await tts_model.synthesize_batch("Hello world")
            
            assert result == b'chunk1chunk2chunk3'
            mock_stream.assert_called_once_with("Hello world", "default", "en", None)
    
    def test_get_available_voices(self, tts_model):
        """Test getting available voices"""
        voices = tts_model.get_available_voices()
        
        assert "default" in voices
        assert voices["default"]["name"] == "Default XTTS Voice"
        assert voices["default"]["language"] == "en"
    
    def test_get_model_info(self, tts_model):
        """Test getting model information"""
        info = tts_model.get_model_info()
        
        assert "model_name" in info
        assert "device" in info
        assert "sample_rate" in info
        assert "available" in info
        assert "initialized" in info
        assert info["sample_rate"] == 24000
    
    @pytest.mark.asyncio
    async def test_stream_audio_file(self, tts_model):
        """Test audio file streaming"""
        # Create temporary WAV file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
            # Write WAV data with multiple frames
            wav_data = b'RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00\x80\x3e\x00\x00\x02\x00\x10\x00data\x08\x00\x00\x00\x00\x00\x01\x00\x02\x00\x03\x00'
            temp_file.write(wav_data)
        
        try:
            chunks = []
            async for chunk in tts_model._stream_audio_file(temp_path):
                chunks.append(chunk)
            
            # Should have at least one chunk
            assert len(chunks) > 0
            assert all(isinstance(chunk, bytes) for chunk in chunks)
        
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    @pytest.mark.asyncio
    async def test_stream_audio_file_error(self, tts_model):
        """Test audio file streaming with invalid file"""
        with pytest.raises(Exception):
            async for chunk in tts_model._stream_audio_file("/nonexistent/file.wav"):
                pass
