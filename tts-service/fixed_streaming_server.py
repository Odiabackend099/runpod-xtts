#!/usr/bin/env python3
"""
Fixed Streaming TTS Server for CallWaiting.ai
Uses robust TTS manager with better error handling
"""

import os
import sys
import asyncio
import tempfile
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Form, File, UploadFile, Request, Depends, Header
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our Robust TTS Manager
sys.path.append(str(Path(__file__).parent))
from robust_tts_manager import robust_tts_manager, VoiceProfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CallWaiting.ai Fixed Streaming TTS Service",
    description="Robust streaming TTS with improved error handling",
    version="2.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str = "default"
    language: str = "en"
    ssml: Optional[str] = None

class VoiceProfileResponse(BaseModel):
    voice_id: str
    name: str
    created_at: str
    language: str
    has_reference_audio: bool

class TenantStatsResponse(BaseModel):
    tenant_id: str
    total_voices: int
    max_voices: int
    rate_limit_per_minute: int

# Authentication dependency
async def verify_api_key(authorization: str = Header(None)) -> str:
    """Verify API key and return tenant_id"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    api_key = authorization.replace("Bearer ", "")
    
    # Find tenant by API key
    for tenant_id, tenant_info in robust_tts_manager.tenants.items():
        if tenant_info.api_key == api_key:
            return tenant_id
    
    raise HTTPException(status_code=401, detail="Invalid API key")

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🚀 Starting CallWaiting.ai Fixed Streaming TTS Service")
    model_info = robust_tts_manager.get_model_info()
    logger.info(f"📊 TTS System: {model_info['system_tts']}")
    logger.info(f"📊 Model Tested: {model_info['tested']}")
    logger.info(f"👥 Tenants configured: {len(robust_tts_manager.tenants)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down TTS service")
    robust_tts_manager.cleanup()

@app.get("/")
async def root():
    """Root endpoint with service information"""
    model_info = robust_tts_manager.get_model_info()
    return {
        "service": "CallWaiting.ai Fixed Streaming TTS Service",
        "version": "2.1.0",
        "status": "running",
        "model_info": model_info,
        "endpoints": {
            "synthesize": "/v1/synthesize",
            "synthesize_streaming": "/v1/synthesize/streaming",
            "voices": "/v1/voices",
            "upload_voice": "/v1/voices/upload",
            "tenant_stats": "/v1/tenant/stats",
            "health": "/v1/health",
            "docs": "/docs"
        },
        "demo_credentials": {
            "api_key": "cw_demo_12345",
            "tenant_id": "callwaiting_demo"
        }
    }

@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    model_info = robust_tts_manager.get_model_info()
    return {
        "status": "healthy",
        "model_loaded": model_info["model_loaded"],
        "streaming_supported": model_info["streaming_supported"],
        "voice_cloning_supported": model_info["voice_cloning_supported"],
        "fallback_mode": model_info["fallback_mode"],
        "system_tts": model_info["system_tts"],
        "tested": model_info["tested"],
        "timestamp": time.time()
    }

@app.get("/v1/voices", response_model=List[VoiceProfileResponse])
async def list_voices(tenant_id: str = Depends(verify_api_key)):
    """List all voice profiles for the authenticated tenant"""
    profiles = robust_tts_manager.list_voice_profiles(tenant_id)
    return profiles

@app.post("/v1/voices/upload")
async def upload_voice(
    voice_file: UploadFile = File(...),
    name: str = Form(...),
    language: str = Form("en"),
    tenant_id: str = Depends(verify_api_key)
):
    """Upload a reference audio file to create a new voice profile"""
    
    # Validate file type
    if not voice_file.content_type or not voice_file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Check file size (max 10MB)
    if voice_file.size and voice_file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    try:
        # Read audio file
        audio_bytes = await voice_file.read()
        
        # Create voice profile
        profile = robust_tts_manager.create_voice_profile(
            tenant_id=tenant_id,
            name=name,
            audio_bytes=audio_bytes,
            language=language
        )
        
        if not profile:
            raise HTTPException(status_code=500, detail="Failed to create voice profile")
        
        return {
            "voice_id": profile.voice_id,
            "name": profile.name,
            "created_at": profile.created_at,
            "language": profile.language,
            "message": "Voice profile created successfully (stored for future Coqui XTTS use)"
        }
        
    except Exception as e:
        logger.error(f"❌ Voice upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Voice upload failed: {str(e)}")

@app.post("/v1/synthesize")
async def synthesize_text(
    request: SynthesizeRequest,
    tenant_id: str = Depends(verify_api_key)
):
    """Synthesize text to speech and return complete audio file"""
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        # Get voice profile
        voice_profile = robust_tts_manager.get_voice_model(tenant_id, request.voice_id)
        if not voice_profile:
            raise HTTPException(status_code=404, detail=f"Voice profile '{request.voice_id}' not found")
        
        logger.info(f"🎤 Synthesizing: '{request.text[:50]}...' with voice '{request.voice_id}'")
        
        # Create temporary file for output
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate audio using robust TTS manager
        start_time = time.time()
        
        # Collect all chunks from streaming inference
        audio_chunks = []
        async for chunk in robust_tts_manager.inference_stream(
            text=request.text,
            voice_profile=voice_profile,
            language=request.language
        ):
            audio_chunks.append(chunk)
        
        # Write all chunks to file
        with open(temp_path, 'wb') as f:
            for chunk in audio_chunks:
                f.write(chunk)
        
        synthesis_time = time.time() - start_time
        file_size = os.path.getsize(temp_path)
        
        logger.info(f"✅ Audio generated in {synthesis_time:.2f} seconds ({file_size:,} bytes)")
        
        # Return the audio file
        return FileResponse(
            temp_path,
            media_type="audio/aiff",
            filename=f"callwaiting_tts_{int(time.time())}.aiff",
            headers={
                "X-Synthesis-Time": str(synthesis_time),
                "X-Voice-ID": request.voice_id,
                "X-Tenant-ID": tenant_id,
                "X-File-Size": str(file_size),
                "X-Text-Length": str(len(request.text)),
                "X-TTS-Method": "robust_system_tts"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@app.post("/v1/synthesize/streaming")
async def synthesize_streaming(
    request: SynthesizeRequest,
    tenant_id: str = Depends(verify_api_key)
):
    """Synthesize text to speech with real-time streaming response"""
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    try:
        # Get voice profile
        voice_profile = robust_tts_manager.get_voice_model(tenant_id, request.voice_id)
        if not voice_profile:
            raise HTTPException(status_code=404, detail=f"Voice profile '{request.voice_id}' not found")
        
        logger.info(f"🌊 Streaming synthesis: '{request.text[:50]}...' with voice '{request.voice_id}'")
        
        # Streaming generator
        async def audio_streamer():
            try:
                async for chunk in robust_tts_manager.inference_stream(
                    text=request.text,
                    voice_profile=voice_profile,
                    language=request.language
                ):
                    yield chunk
            except Exception as e:
                logger.error(f"❌ Streaming error: {e}")
                # Send error as audio metadata
                error_msg = f"Error: {str(e)}"
                yield error_msg.encode()
        
        return StreamingResponse(
            audio_streamer(),
            media_type="audio/aiff",
            headers={
                "X-Voice-ID": request.voice_id,
                "X-Tenant-ID": tenant_id,
                "X-Streaming": "true",
                "X-Text-Length": str(len(request.text)),
                "X-TTS-Method": "robust_system_tts"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Streaming synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming synthesis failed: {str(e)}")

@app.get("/v1/tenant/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(tenant_id: str = Depends(verify_api_key)):
    """Get statistics for the authenticated tenant"""
    tenant_info = robust_tts_manager.get_tenant_info(tenant_id)
    if not tenant_info:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    voice_count = len(robust_tts_manager.voice_profiles.get(tenant_id, {}))
    
    return TenantStatsResponse(
        tenant_id=tenant_id,
        total_voices=voice_count,
        max_voices=tenant_info.max_voices,
        rate_limit_per_minute=tenant_info.rate_limit_per_minute
    )

@app.post("/v1/generate-demo-audio")
async def generate_demo_audio(tenant_id: str = Depends(verify_api_key)):
    """Generate demo audio files for the tenant"""
    
    demo_texts = [
        {
            "text": "Hello, this is CallWaiting.ai TTS service. We provide high-quality voice synthesis for your business needs.",
            "filename": f"callwaiting_intro_{tenant_id}.aiff",
            "description": "Service Introduction"
        },
        {
            "text": "Welcome to CallWaiting.ai, your premier telecommunications solution with advanced TTS technology.",
            "filename": f"callwaiting_welcome_{tenant_id}.aiff", 
            "description": "Welcome Message"
        },
        {
            "text": "Thank you for calling CallWaiting.ai. Your call is important to us. Please hold while we connect you.",
            "filename": f"callwaiting_hold_{tenant_id}.aiff",
            "description": "Hold Message"
        },
        {
            "text": "This is a demonstration of our robust streaming TTS technology. The audio is generated reliably using advanced voice synthesis.",
            "filename": f"callwaiting_robust_demo_{tenant_id}.aiff",
            "description": "Robust Technology Demo"
        }
    ]
    
    generated_files = []
    
    try:
        # Get default voice profile
        voice_profile = robust_tts_manager.get_voice_model(tenant_id, "default")
        if not voice_profile:
            raise HTTPException(status_code=404, detail="Default voice profile not found")
        
        for demo in demo_texts:
            logger.info(f"🎤 Generating: {demo['description']}")
            
            # Generate audio using robust streaming inference
            start_time = time.time()
            audio_chunks = []
            
            async for chunk in robust_tts_manager.inference_stream(
                text=demo["text"],
                voice_profile=voice_profile,
                language="en"
            ):
                audio_chunks.append(chunk)
            
            # Write to file
            with open(demo["filename"], 'wb') as f:
                for chunk in audio_chunks:
                    f.write(chunk)
            
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
            "total_files": len(generated_files),
            "tenant_id": tenant_id,
            "tts_method": "robust_system_tts"
        }
        
    except Exception as e:
        logger.error(f"❌ Demo generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Demo generation failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting CallWaiting.ai Fixed Streaming TTS Service")
    print("📡 Service will be available at: http://localhost:8000")
    print("🎤 Streaming TTS endpoint: POST http://localhost:8000/v1/synthesize/streaming")
    print("🎵 Voice upload: POST http://localhost:8000/v1/voices/upload")
    print("📚 API docs: http://localhost:8000/docs")
    print("🔑 Demo API Key: cw_demo_12345 (for tenant: callwaiting_demo)")
    print("🔑 Test API Key: test_key_67890 (for tenant: test_tenant)")
    print("🛠️  Using robust TTS manager with improved error handling")
    
    uvicorn.run(
        "fixed_streaming_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
