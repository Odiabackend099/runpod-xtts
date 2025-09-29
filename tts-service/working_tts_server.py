#!/usr/bin/env python3
"""
Working TTS Server for CallWaiting.ai
Uses the local Coqui TTS repository for better compatibility
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

# Add the Coqui TTS repository to Python path
coqui_path = Path(__file__).parent.parent / "coqui-tts"
sys.path.insert(0, str(coqui_path))

# Set TTS license agreement
os.environ["TTS_AGREE_TO_CPML"] = "1"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    
    try:
        logger.info("🚀 Loading Coqui XTTS model from local repository...")
        
        # Import TTS from local repository
        from TTS.api import TTS
        
        # Load XTTS model
        tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        
        logger.info("✅ XTTS model loaded successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to load TTS model: {e}")
        # Don't raise - let the service start in degraded mode

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CallWaiting.ai TTS Service",
        "status": "running",
        "model_loaded": tts_model is not None,
        "endpoints": {
            "synthesize": "/synthesize",
            "health": "/health",
            "voices": "/voices",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if tts_model else "degraded",
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
            filename=f"callwaiting_tts_{int(time.time())}.wav",
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

@app.post("/generate-demo-audio")
async def generate_demo_audio():
    """
    Generate demo audio files for CallWaiting.ai
    """
    if not tts_model:
        raise HTTPException(status_code=503, detail="TTS model not loaded")
    
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
        }
    ]
    
    generated_files = []
    
    try:
        for demo in demo_texts:
            logger.info(f"🎤 Generating: {demo['description']}")
            
            # Generate audio
            start_time = time.time()
            tts_model.tts_to_file(
                text=demo["text"],
                file_path=demo["filename"],
                language="en"
            )
            synthesis_time = time.time() - start_time
            
            if os.path.exists(demo["filename"]):
                file_size = os.path.getsize(demo["filename"])
                generated_files.append({
                    "filename": demo["filename"],
                    "description": demo["description"],
                    "size": file_size,
                    "synthesis_time": synthesis_time
                })
                logger.info(f"✅ Generated {demo['filename']} ({file_size:,} bytes)")
        
        return {
            "message": "Demo audio files generated successfully",
            "files": generated_files,
            "total_files": len(generated_files)
        }
        
    except Exception as e:
        logger.error(f"❌ Demo generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Demo generation failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting CallWaiting.ai TTS Service")
    print("📡 Service will be available at: http://localhost:8000")
    print("🎤 TTS endpoint: POST http://localhost:8000/synthesize")
    print("📚 API docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "working_tts_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
