"""
Coqui XTTS Model Wrapper for Streaming TTS
Provides high-quality neural voice synthesis with streaming support
"""

import os
import asyncio
import tempfile
import wave
import struct
from typing import AsyncGenerator, Optional, Dict, Any
from pathlib import Path
import logging

try:
    from TTS.api import TTS
    from TTS.tts.configs.xtts_config import XttsConfig
    from TTS.tts.models.xtts import Xtts
    import torch
    import torchaudio
    COQUI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Coqui TTS not available: {e}")
    COQUI_AVAILABLE = False

logger = logging.getLogger(__name__)

class CoquiXTTSModel:
    """High-performance Coqui XTTS model wrapper with streaming support"""
    
    def __init__(self, model_path: str = "tts_models/multilingual/multi-dataset/xtts_v2"):
        self.model_path = model_path
        self.model = None
        self.config = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.sample_rate = 24000
        self.chunk_size = 1024  # Audio chunk size for streaming
        
        # Set license agreement environment variable
        os.environ["TTS_AGREE_TO_CPML"] = "1"
        
    async def initialize(self):
        """Initialize the XTTS model asynchronously"""
        if not COQUI_AVAILABLE:
            raise RuntimeError("Coqui TTS is not available")
            
        try:
            logger.info(f"Loading XTTS model: {self.model_path}")
            logger.info(f"Using device: {self.device}")
            
            # Load XTTS model
            self.model = TTS(model_name=self.model_path, progress_bar=False)
            
            logger.info("✅ XTTS model loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load XTTS model: {e}")
            raise
    
    async def synthesize_streaming(
        self, 
        text: str, 
        voice_id: str = "default",
        language: str = "en",
        reference_audio: Optional[str] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate streaming audio using XTTS
        
        Args:
            text: Text to synthesize
            voice_id: Voice identifier
            language: Language code
            reference_audio: Path to reference audio for voice cloning
            
        Yields:
            Audio chunks as bytes
        """
        if not self.model:
            raise RuntimeError("Model not initialized")
        
        try:
            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio using XTTS
            if reference_audio and os.path.exists(reference_audio):
                # Voice cloning mode
                self.model.tts_to_file(
                    text=text,
                    file_path=temp_path,
                    speaker_wav=reference_audio,
                    language=language
                )
            else:
                # Standard synthesis
                self.model.tts_to_file(
                    text=text,
                    file_path=temp_path,
                    language=language
                )
            
            # Stream the generated audio in chunks
            async for chunk in self._stream_audio_file(temp_path):
                yield chunk
                
            # Cleanup
            os.unlink(temp_path)
            
        except Exception as e:
            logger.error(f"Error in streaming synthesis: {e}")
            raise
    
    async def _stream_audio_file(self, file_path: str) -> AsyncGenerator[bytes, None]:
        """Stream audio file in chunks"""
        try:
            with wave.open(file_path, 'rb') as wav_file:
                # Read audio data in chunks
                while True:
                    chunk = wav_file.readframes(self.chunk_size)
                    if not chunk:
                        break
                    yield chunk
                    
        except Exception as e:
            logger.error(f"Error streaming audio file: {e}")
            raise
    
    async def synthesize_batch(
        self, 
        text: str, 
        voice_id: str = "default",
        language: str = "en",
        reference_audio: Optional[str] = None
    ) -> bytes:
        """
        Generate complete audio file (batch mode)
        
        Returns:
            Complete audio data as bytes
        """
        audio_data = b""
        async for chunk in self.synthesize_streaming(text, voice_id, language, reference_audio):
            audio_data += chunk
        return audio_data
    
    def get_available_voices(self) -> Dict[str, Any]:
        """Get list of available voices"""
        return {
            "default": {
                "name": "Default XTTS Voice",
                "language": "en",
                "description": "High-quality neural voice from XTTS v2"
            }
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model information and status"""
        return {
            "model_name": self.model_path,
            "device": self.device,
            "sample_rate": self.sample_rate,
            "available": COQUI_AVAILABLE,
            "initialized": self.model is not None
        }
