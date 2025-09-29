#!/usr/bin/env python3
"""
Real TTS Server using Microsoft Edge TTS
High-quality neural voices for CallWaiting.ai
"""

import asyncio
import logging
import tempfile
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import edge_tts
import uvicorn
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CallWaiting.ai Real TTS Service",
    description="High-quality TTS microservice using Microsoft Edge TTS",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Demo tenants
TENANTS = {
    "cw_demo_12345": {
        "tenant_id": "callwaiting_demo",
        "name": "CallWaiting.ai Demo",
        "rate_limit": 1000,
        "voices": list(EDGE_VOICES.keys())
    },
    "test_key_67890": {
        "tenant_id": "test_tenant", 
        "name": "Test Tenant",
        "rate_limit": 100,
        "voices": ["default", "professional"]
    }
}

class RealTTSManager:
    """Real TTS Manager using Microsoft Edge TTS"""
    
    def __init__(self):
        self.voices = EDGE_VOICES
        logger.info("🎤 Real TTS Manager initialized with Edge TTS")
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
            raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")
    
    async def synthesize_streaming(self, text: str, voice_id: str = "default", language: str = "en"):
        """Stream audio synthesis using Edge TTS"""
        try:
            voice_name = self.voices.get(voice_id, self.voices["default"])
            logger.info(f"🌊 Streaming synthesis with Edge TTS: voice={voice_name}")
            
            communicate = edge_tts.Communicate(text, voice_name)
            
            async def audio_generator():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        yield chunk["data"]
            
            return audio_generator()
            
        except Exception as e:
            logger.error(f"❌ Edge TTS streaming failed: {e}")
            raise HTTPException(status_code=500, detail=f"Streaming synthesis failed: {str(e)}")

# Initialize TTS manager
tts_manager = RealTTSManager()

def get_current_tenant(request: Request) -> Dict[str, Any]:
    """Get current tenant from API key"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    
    if not api_key or api_key not in TENANTS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return TENANTS[api_key]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CallWaiting.ai Real TTS Service",
        "version": "1.0.0",
        "engine": "Microsoft Edge TTS",
        "status": "operational",
        "endpoints": {
            "health": "/v1/health",
            "synthesize": "/v1/synthesize",
            "streaming": "/v1/synthesize/streaming",
            "voices": "/v1/voices",
            "docs": "/docs"
        }
    }

@app.get("/v1/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "engine": "Microsoft Edge TTS",
        "voices_available": len(EDGE_VOICES),
        "tenants_configured": len(TENANTS)
    }

@app.get("/v1/voices")
async def get_voices(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """Get available voices for tenant"""
    tenant_voices = tenant_info.get("voices", ["default"])
    
    voices = []
    for voice_id in tenant_voices:
        if voice_id in EDGE_VOICES:
            voices.append({
                "id": voice_id,
                "name": voice_id.replace("_", " ").title(),
                "language": "en-US",
                "neural": True,
                "edge_voice": EDGE_VOICES[voice_id]
            })
    
    return {
        "voices": voices,
        "total": len(voices),
        "tenant": tenant_info["tenant_id"]
    }

@app.post("/v1/synthesize")
async def synthesize_text(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en"),
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """Synthesize text to speech"""
    try:
        # Validate voice access
        if voice_id not in tenant_info.get("voices", []):
            voice_id = "default"
        
        logger.info(f"🎤 Synthesizing: '{text[:50]}...' with voice '{voice_id}'")
        
        # Generate audio
        audio_data = await tts_manager.synthesize(text, voice_id, language)
        
        logger.info(f"✅ Audio generated: {len(audio_data)} bytes")
        
        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=synthesis.mp3",
                "X-Tenant-ID": tenant_info["tenant_id"],
                "X-Voice-ID": voice_id,
                "X-Engine": "Edge-TTS"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@app.post("/v1/synthesize/streaming")
async def synthesize_streaming(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en"),
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """Stream audio synthesis"""
    try:
        # Validate voice access
        if voice_id not in tenant_info.get("voices", []):
            voice_id = "default"
        
        logger.info(f"🌊 Streaming synthesis: '{text[:50]}...' with voice '{voice_id}'")
        
        # Generate streaming audio
        audio_generator = await tts_manager.synthesize_streaming(text, voice_id, language)
        
        return StreamingResponse(
            audio_generator,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=streaming_synthesis.mp3",
                "X-Tenant-ID": tenant_info["tenant_id"],
                "X-Voice-ID": voice_id,
                "X-Engine": "Edge-TTS",
                "X-Streaming": "true"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Streaming synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Streaming synthesis failed: {str(e)}")

@app.get("/v1/tenant/stats")
async def get_tenant_stats(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """Get tenant statistics"""
    return {
        "tenant_id": tenant_info["tenant_id"],
        "tenant_name": tenant_info["name"],
        "rate_limit": tenant_info["rate_limit"],
        "available_voices": len(tenant_info.get("voices", [])),
        "engine": "Microsoft Edge TTS",
        "status": "active"
    }

@app.post("/v1/generate-demo-audio")
async def generate_demo_audio(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """Generate demo audio files"""
    try:
        demos = [
            {
                "name": "Service Introduction",
                "text": "Welcome to CallWaiting.ai. We provide advanced telecommunications solutions with high-quality voice synthesis technology.",
                "voice": "default"
            },
            {
                "name": "Professional Greeting", 
                "text": "Thank you for calling. Please hold while we connect you to the next available representative.",
                "voice": "professional"
            },
            {
                "name": "Friendly Message",
                "text": "Hello! We're excited to help you today. How can we assist you with your telecommunications needs?",
                "voice": "friendly"
            }
        ]
        
        results = []
        for demo in demos:
            try:
                audio_data = await tts_manager.synthesize(
                    demo["text"], 
                    demo["voice"], 
                    "en"
                )
                
                filename = f"demo_{demo['name'].lower().replace(' ', '_')}_{tenant_info['tenant_id']}.mp3"
                
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                
                results.append({
                    "name": demo["name"],
                    "filename": filename,
                    "size": len(audio_data),
                    "voice": demo["voice"],
                    "status": "generated"
                })
                
                logger.info(f"✅ Generated {filename} ({len(audio_data)} bytes)")
                
            except Exception as e:
                results.append({
                    "name": demo["name"],
                    "error": str(e),
                    "status": "failed"
                })
        
        return {
            "demos": results,
            "total_generated": len([r for r in results if r["status"] == "generated"]),
            "tenant": tenant_info["tenant_id"]
        }
        
    except Exception as e:
        logger.error(f"❌ Demo generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Demo generation failed: {str(e)}")

if __name__ == "__main__":
    print("🚀 Starting CallWaiting.ai Real TTS Service")
    print("📡 Service will be available at: http://localhost:8000")
    print("🎤 Real TTS endpoint: POST http://localhost:8000/v1/synthesize")
    print("🌊 Streaming endpoint: POST http://localhost:8000/v1/synthesize/streaming")
    print("📚 API docs: http://localhost:8000/docs")
    print("🔑 Demo API Key: cw_demo_12345 (for tenant: callwaiting_demo)")
    print("🔑 Test API Key: test_key_67890 (for tenant: test_tenant)")
    print("🎵 Using Microsoft Edge TTS with high-quality neural voices")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
