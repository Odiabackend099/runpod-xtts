#!/usr/bin/env python3
"""
Simple TTS Server for Real Audio Generation
Generates actual audio using Coqui XTTS without complex dependencies
"""

import os
import sys
import asyncio
import tempfile
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set TTS license agreement
os.environ["TTS_AGREE_TO_CPML"] = "1"

try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    logger.error("TTS not available. Please install: pip install TTS")

app = FastAPI(
    title="CallWaiting.ai TTS Service",
    description="Real TTS audio generation using Coqui XTTS",
    version="1.0.0"
)

# Global TTS model
tts_model = None

@app.on_event("startup")
async def startup_event():
    """Initialize TTS model on startup"""
    global tts_model
    
    if not TTS_AVAILABLE:
        logger.error("TTS not available - cannot start service")
        return
    
    try:
        logger.info("🚀 Loading Coqui XTTS model...")
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        logger.info("✅ XTTS model loaded successfully!")
    except Exception as e:
        logger.error(f"❌ Failed to load TTS model: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CallWaiting.ai TTS Service",
        "status": "running",
        "tts_available": TTS_AVAILABLE,
        "model_loaded": tts_model is not None,
        "endpoints": {
            "synthesize": "/synthesize",
            "health": "/health",
            "voices": "/voices"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if tts_model else "degraded",
        "tts_available": TTS_AVAILABLE,
        "model_loaded": tts_model is not None,
        "timestamp": time.time()
    }

@app.get("/voices")
async def get_voices():
    """Get available voices"""
    return {
        "voices": [
            {
                "voice_id": "naija_female",
                "name": "Nigerian Female",
                "description": "High-quality Nigerian female voice",
                "language": "en"
            },
            {
                "voice_id": "naija_male", 
                "name": "Nigerian Male",
                "description": "High-quality Nigerian male voice",
                "language": "en"
            },
            {
                "voice_id": "default",
                "name": "Default Voice",
                "description": "Default XTTS neural voice",
                "language": "en"
            }
        ]
    }

@app.post("/synthesize")
async def synthesize_text(
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en")
):
    """
    Synthesize text to speech and return real audio file
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        logger.info(f"🎤 Synthesizing: '{text[:50]}...' with voice '{voice_id}'")
        
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate audio using XTTS
        start_time = time.time()
        tts_model.tts_to_file(
            text=text,
            file_path=temp_path,
            language=language
        )
        synthesis_time = time.time() - start_time
        
        logger.info(f"✅ Audio generated in {synthesis_time:.2f} seconds")
        
        # Return the audio file
        return FileResponse(
            temp_path,
            media_type="audio/wav",
            filename=f"tts_output_{int(time.time())}.wav",
            headers={
                "X-Synthesis-Time": str(synthesis_time),
                "X-Voice-ID": voice_id,
                "X-Text-Length": str(len(text))
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@app.post("/synthesize-streaming")
async def synthesize_streaming(
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en")
):
    """
    Synthesize text to speech with streaming response
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    try:
        logger.info(f"🌊 Streaming synthesis: '{text[:50]}...'")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate audio
        tts_model.tts_to_file(
            text=text,
            file_path=temp_path,
            language=language
        )
        
        # Stream the file
        def generate():
            with open(temp_path, 'rb') as f:
                while True:
                    chunk = f.read(1024)
                    if not chunk:
                        break
                    yield chunk
            # Cleanup
            os.unlink(temp_path)
        
        return StreamingResponse(
            generate(),
            media_type="audio/wav",
            headers={
                "X-Voice-ID": voice_id,
                "X-Streaming": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Streaming synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming failed: {str(e)}")

@app.post("/upload-voice")
async def upload_voice(
    voice_id: str = Form(...),
    name: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    Upload reference audio for voice cloning
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    try:
        # Save uploaded file
        audio_data = await audio_file.read()
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file.write(audio_data)
            reference_path = temp_file.name
        
        logger.info(f"🎤 Voice uploaded: {voice_id} ({len(audio_data)} bytes)")
        
        return {
            "message": "Voice uploaded successfully",
            "voice_id": voice_id,
            "name": name,
            "reference_path": reference_path,
            "file_size": len(audio_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Voice upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/synthesize-with-voice")
async def synthesize_with_voice(
    text: str = Form(...),
    voice_id: str = Form(...),
    reference_audio_path: str = Form(...),
    language: str = Form("en")
):
    """
    Synthesize text using uploaded reference voice
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
    if not os.path.exists(reference_audio_path):
        raise HTTPException(status_code=404, detail="Reference audio not found")
    
    try:
        logger.info(f"🎤 Voice cloning synthesis: '{text[:50]}...'")
        
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate audio with voice cloning
        start_time = time.time()
        tts_model.tts_to_file(
            text=text,
            file_path=temp_path,
            speaker_wav=reference_audio_path,
            language=language
        )
        synthesis_time = time.time() - start_time
        
        logger.info(f"✅ Voice cloned audio generated in {synthesis_time:.2f} seconds")
        
        return FileResponse(
            temp_path,
            media_type="audio/wav",
            filename=f"cloned_voice_{int(time.time())}.wav",
            headers={
                "X-Synthesis-Time": str(synthesis_time),
                "X-Voice-ID": voice_id,
                "X-Voice-Cloning": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Voice cloning failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice cloning failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting CallWaiting.ai TTS Service")
    print("📡 Service will be available at: http://localhost:8000")
    print("🎤 TTS endpoint: POST http://localhost:8000/synthesize")
    print("📚 API docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "simple_tts_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
