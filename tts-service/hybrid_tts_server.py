#!/usr/bin/env python3
"""
Hybrid TTS Server for CallWaiting.ai
Combines system TTS for immediate audio generation with TTS service API
"""

import os
import sys
import asyncio
import tempfile
import time
import subprocess
from pathlib import Path
from fastapi import FastAPI, HTTPException, Form, File, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
import uvicorn
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CallWaiting.ai TTS Service",
    description="Real TTS audio generation with system TTS and Coqui XTTS support",
    version="1.0.0"
)

# Global TTS model (will be None if Coqui TTS not available)
tts_model = None
coqui_available = False

@app.on_event("startup")
async def startup_event():
    """Initialize TTS model on startup"""
    global tts_model, coqui_available
    
    try:
        logger.info("🚀 Attempting to load Coqui XTTS model...")
        
        # Try to import TTS from local repository
        coqui_path = Path(__file__).parent.parent / "coqui-tts"
        sys.path.insert(0, str(coqui_path))
        
        from TTS.api import TTS
        
        # Load XTTS model
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        coqui_available = True
        
        logger.info("✅ Coqui XTTS model loaded successfully!")
        
    except Exception as e:
        logger.warning(f"⚠️  Coqui XTTS not available: {e}")
        logger.info("🔄 Falling back to system TTS for audio generation")
        coqui_available = False

def generate_audio_system_tts(text: str, output_file: str) -> bool:
    """Generate audio using system TTS (macOS say command)"""
    try:
        # Use macOS say command to generate audio
        cmd = ["say", "-o", output_file, text]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and os.path.exists(output_file):
            return True
        else:
            logger.error(f"System TTS failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"System TTS error: {e}")
        return False

def generate_audio_coqui_tts(text: str, output_file: str, language: str = "en") -> bool:
    """Generate audio using Coqui XTTS"""
    if not tts_model:
        return False
        
    try:
        tts_model.tts_to_file(
            text=text,
            file_path=output_file,
            language=language
        )
        return os.path.exists(output_file)
    except Exception as e:
        logger.error(f"Coqui TTS error: {e}")
        return False

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CallWaiting.ai TTS Service",
        "status": "running",
        "coqui_available": coqui_available,
        "system_tts_available": True,
        "endpoints": {
            "synthesize": "/synthesize",
            "health": "/health",
            "voices": "/voices",
            "generate_demo": "/generate-demo-audio",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "coqui_available": coqui_available,
        "system_tts_available": True,
        "model_loaded": tts_model is not None,
        "timestamp": time.time()
    }

@app.get("/voices")
async def get_voices():
    """Get available voices"""
    voices = [
        {
            "voice_id": "system_default",
            "name": "System Default Voice",
            "description": "High-quality system voice",
            "language": "en",
            "type": "system"
        }
    ]
    
    if coqui_available:
        voices.extend([
            {
                "voice_id": "naija_female",
                "name": "Nigerian Female",
                "description": "High-quality Nigerian female voice",
                "language": "en",
                "type": "coqui"
            },
            {
                "voice_id": "naija_male", 
                "name": "Nigerian Male",
                "description": "High-quality Nigerian male voice",
                "language": "en",
                "type": "coqui"
            },
            {
                "voice_id": "default",
                "name": "Default XTTS Voice",
                "description": "Default XTTS neural voice",
                "language": "en",
                "type": "coqui"
            }
        ])
    
    return {"voices": voices}

@app.post("/synthesize")
async def synthesize_text(
    text: str = Form(...),
    voice_id: str = Form("system_default"),
    language: str = Form("en"),
    use_coqui: bool = Form(False)
):
    """
    Synthesize text to speech and return real audio file
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        logger.info(f"🎤 Synthesizing: '{text[:50]}...' with voice '{voice_id}'")
        
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Choose TTS method
        success = False
        synthesis_time = 0
        
        if use_coqui and coqui_available:
            logger.info("🔄 Using Coqui XTTS...")
            start_time = time.time()
            success = generate_audio_coqui_tts(text, temp_path, language)
            synthesis_time = time.time() - start_time
        else:
            logger.info("🔄 Using system TTS...")
            start_time = time.time()
            success = generate_audio_system_tts(text, temp_path)
            synthesis_time = time.time() - start_time
        
        if not success:
            raise HTTPException(status_code=500, detail="Audio generation failed")
        
        logger.info(f"✅ Audio generated in {synthesis_time:.2f} seconds")
        
        # Return the audio file
        return FileResponse(
            temp_path,
            media_type="audio/wav",
            filename=f"callwaiting_tts_{int(time.time())}.wav",
            headers={
                "X-Synthesis-Time": str(synthesis_time),
                "X-Voice-ID": voice_id,
                "X-TTS-Method": "coqui" if (use_coqui and coqui_available) else "system",
                "X-Text-Length": str(len(text))
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@app.post("/generate-demo-audio")
async def generate_demo_audio():
    """
    Generate demo audio files for CallWaiting.ai
    """
    demo_texts = [
        {
            "text": "Hello, this is CallWaiting.ai TTS service. We provide high-quality voice synthesis for your business needs.",
            "filename": "callwaiting_intro_demo.wav",
            "description": "Service Introduction"
        },
        {
            "text": "Welcome to CallWaiting.ai, your premier telecommunications solution with advanced TTS technology.",
            "filename": "callwaiting_welcome_demo.wav", 
            "description": "Welcome Message"
        },
        {
            "text": "Thank you for calling CallWaiting.ai. Your call is important to us. Please hold while we connect you.",
            "filename": "callwaiting_hold_demo.wav",
            "description": "Hold Message"
        },
        {
            "text": "This is a demonstration of our high-quality voice synthesis technology. The voice sounds natural and professional.",
            "filename": "callwaiting_tech_demo.wav",
            "description": "Technology Demo"
        }
    ]
    
    generated_files = []
    
    try:
        for demo in demo_texts:
            logger.info(f"🎤 Generating: {demo['description']}")
            
            # Generate audio using system TTS
            start_time = time.time()
            success = generate_audio_system_tts(demo["text"], demo["filename"])
            synthesis_time = time.time() - start_time
            
            if success and os.path.exists(demo["filename"]):
                file_size = os.path.getsize(demo["filename"])
                generated_files.append({
                    "filename": demo["filename"],
                    "description": demo["description"],
                    "size": file_size,
                    "synthesis_time": synthesis_time,
                    "tts_method": "system"
                })
                logger.info(f"✅ Generated {demo['filename']} ({file_size:,} bytes)")
        
        return {
            "message": "Demo audio files generated successfully",
            "files": generated_files,
            "total_files": len(generated_files),
            "coqui_available": coqui_available
        }
        
    except Exception as e:
        logger.error(f"❌ Demo generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Demo generation failed: {str(e)}")

@app.post("/test-coqui")
async def test_coqui():
    """
    Test Coqui XTTS functionality
    """
    if not coqui_available:
        return {
            "status": "unavailable",
            "message": "Coqui XTTS not available",
            "reason": "Dependencies not installed or model loading failed"
        }
    
    try:
        test_text = "Hello, this is a test of Coqui XTTS voice synthesis."
        test_file = "coqui_test.wav"
        
        start_time = time.time()
        success = generate_audio_coqui_tts(test_text, test_file)
        synthesis_time = time.time() - start_time
        
        if success and os.path.exists(test_file):
            file_size = os.path.getsize(test_file)
            return {
                "status": "success",
                "message": "Coqui XTTS working correctly",
                "test_file": test_file,
                "file_size": file_size,
                "synthesis_time": synthesis_time
            }
        else:
            return {
                "status": "failed",
                "message": "Coqui XTTS test failed"
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Coqui XTTS test error: {str(e)}"
        }

if __name__ == "__main__":
    print("🚀 Starting CallWaiting.ai Hybrid TTS Service")
    print("📡 Service will be available at: http://localhost:8000")
    print("🎤 TTS endpoint: POST http://localhost:8000/synthesize")
    print("🎵 Demo generation: POST http://localhost:8000/generate-demo-audio")
    print("📚 API docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "hybrid_tts_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
