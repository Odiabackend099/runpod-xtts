#!/usr/bin/env python3
"""
RunPod Serverless Handler for CallWaiting.ai TTS Service
Deploy your TTS service on RunPod's serverless infrastructure
"""

import runpod
import asyncio
import json
import base64
import tempfile
import os
from typing import Dict, Any, Optional
import edge_tts
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available Edge TTS voices
EDGE_VOICES = {
    "default": "en-US-AriaNeural",
    "naija_female": "en-US-JennyNeural", 
    "naija_male": "en-US-GuyNeural",
    "professional": "en-US-DavisNeural",
    "friendly": "en-US-EmmaNeural",
    "calm": "en-US-MichelleNeural",
    "energetic": "en-US-BrianNeural"
}

class RunPodTTSHandler:
    """TTS Handler for RunPod Serverless"""
    
    def __init__(self):
        self.voices = EDGE_VOICES
        logger.info("🎤 RunPod TTS Handler initialized with Edge TTS")
        logger.info(f"📊 Available voices: {list(self.voices.keys())}")
    
    async def synthesize(self, text: str, voice_id: str = "default", language: str = "en") -> bytes:
        """Synthesize text to speech using Edge TTS"""
        try:
            # Get voice name
            voice_name = self.voices.get(voice_id, self.voices["default"])
            
            logger.info(f"🎤 Synthesizing with Edge TTS: voice={voice_name}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate speech
            communicate = edge_tts.Communicate(text, voice_name)
            await communicate.save(temp_path)
            
            # Read audio data
            with open(temp_path, 'rb') as f:
                audio_data = f.read()
            
            # Clean up
            os.unlink(temp_path)
            
            logger.info(f"✅ Edge TTS synthesis completed: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ Edge TTS synthesis failed: {e}")
            raise Exception(f"TTS synthesis failed: {str(e)}")

# Initialize handler
tts_handler = RunPodTTSHandler()

def handler(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    RunPod Serverless Handler Function
    
    Expected input format:
    {
        "input": {
            "text": "Hello, this is a test",
            "voice_id": "default",
            "language": "en"
        }
    }
    
    Returns:
    {
        "audio_base64": "base64_encoded_audio_data",
        "audio_size": 12345,
        "voice_used": "en-US-AriaNeural",
        "status": "success"
    }
    """
    try:
        # Extract input parameters
        input_data = event.get("input", {})
        text = input_data.get("text", "")
        voice_id = input_data.get("voice_id", "default")
        language = input_data.get("language", "en")
        
        # Validate input
        if not text:
            return {
                "error": "No text provided",
                "status": "error"
            }
        
        if len(text) > 5000:  # Limit text length
            return {
                "error": "Text too long (max 5000 characters)",
                "status": "error"
            }
        
        logger.info(f"🎤 Processing TTS request: '{text[:50]}...' with voice '{voice_id}'")
        
        # Generate audio
        audio_data = asyncio.run(tts_handler.synthesize(text, voice_id, language))
        
        # Encode audio as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Get voice name used
        voice_used = EDGE_VOICES.get(voice_id, EDGE_VOICES["default"])
        
        logger.info(f"✅ TTS request completed successfully: {len(audio_data)} bytes")
        
        return {
            "audio_base64": audio_base64,
            "audio_size": len(audio_data),
            "voice_used": voice_used,
            "voice_id": voice_id,
            "text_length": len(text),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ Handler error: {e}")
        return {
            "error": str(e),
            "status": "error"
        }

# Register the handler with RunPod
runpod.serverless.start({"handler": handler})
