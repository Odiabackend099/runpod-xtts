#!/usr/bin/env python3
"""
CallWaiting.ai TTS Service - Supreme Command Compliant
High-performance Text-to-Speech microservice using Microsoft Edge TTS
"""

import os
import asyncio
import logging
import tempfile
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, Response, HTTPException, Depends, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import edge_tts
import json
import time
import psutil
from collections import defaultdict

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
    "energetic": "en-US-BrandonNeural"
}

# Demo API keys for testing
DEMO_API_KEYS = {
    "cw_demo_12345": {"tenant_id": "callwaiting_demo", "name": "Demo Tenant"},
    "test_key_67890": {"tenant_id": "test_tenant", "name": "Test Tenant"}
}

# Metrics tracking
metrics = {
    "requests_total": 0,
    "requests_by_tenant": defaultdict(int),
    "requests_by_voice": defaultdict(int),
    "total_audio_generated": 0,
    "start_time": time.time()
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🎤 Real TTS Manager initialized with Edge TTS")
    logger.info(f"📊 Available voices: {list(EDGE_VOICES.keys())}")
    yield
    logger.info("🔄 Shutting down TTS service")

app = FastAPI(
    title="CallWaiting.ai TTS Service",
    description="High-performance TTS microservice using Microsoft Edge TTS",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def validate_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    """Validate API key and return tenant info"""
    return DEMO_API_KEYS.get(api_key)

async def get_current_tenant(request: Request) -> Dict[str, Any]:
    """Get current tenant from API key"""
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    tenant_info = validate_api_key(api_key)
    if not tenant_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return tenant_info

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "CallWaiting.ai TTS Service",
        "status": "running",
        "version": "1.0.0",
        "engine": "Microsoft Edge TTS"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "TTS",
        "uptime": time.time() - metrics["start_time"],
        "requests_total": metrics["requests_total"]
    }

@app.get("/voices")
async def list_voices(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """List available voices"""
    return {
        "voices": [
            {
                "id": voice_id,
                "name": voice_id.replace("_", " ").title(),
                "description": f"Microsoft Edge TTS voice: {edge_voice}",
                "language": "en-US",
                "gender": "female" if "female" in voice_id else "male" if "male" in voice_id else "neutral"
            }
            for voice_id, edge_voice in EDGE_VOICES.items()
        ]
    }

@app.post("/synthesize")
async def synthesize_text(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en"),
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """Synthesize text to speech"""
    try:
        # Validate voice
        if voice_id not in EDGE_VOICES:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid voice_id. Available voices: {list(EDGE_VOICES.keys())}"
            )
        
        # Update metrics
        metrics["requests_total"] += 1
        metrics["requests_by_tenant"][tenant_info["tenant_id"]] += 1
        metrics["requests_by_voice"][voice_id] += 1
        
        logger.info(f"🎤 Synthesizing: '{text[:50]}...' with voice '{voice_id}'")
        
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Generate speech using Edge TTS
        edge_voice = EDGE_VOICES[voice_id]
        logger.info(f"🎤 Synthesizing with Edge TTS: voice={edge_voice}")
        
        communicate = edge_tts.Communicate(text, edge_voice)
        await communicate.save(temp_path)
        
        # Read audio data
        with open(temp_path, 'rb') as f:
            audio_data = f.read()
        
        # Clean up
        os.unlink(temp_path)
        
        # Update metrics
        metrics["total_audio_generated"] += len(audio_data)
        
        logger.info(f"✅ Edge TTS synthesis completed: {len(audio_data)} bytes")
        logger.info(f"✅ Audio generated: {len(audio_data)} bytes")
        
        return Response(content=audio_data, media_type="audio/mpeg")
        
    except Exception as e:
        logger.error(f"❌ Synthesis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Synthesis failed: {str(e)}")

@app.get("/tenant/stats")
async def get_tenant_stats(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """Get tenant statistics"""
    return {
        "tenant_id": tenant_info["tenant_id"],
        "tenant_name": tenant_info["name"],
        "requests_count": metrics["requests_by_tenant"][tenant_info["tenant_id"]],
        "total_requests": metrics["requests_total"],
        "uptime": time.time() - metrics["start_time"]
    }

if __name__ == "__main__":
    print("🚀 Starting CallWaiting.ai Real TTS Service")
    print("📡 Service will be available at: http://localhost:8000")
    print("🎤 Real TTS endpoint: POST http://localhost:8000/synthesize")
    print("📚 API docs: http://localhost:8000/docs")
    print("🔑 Demo API Key: cw_demo_12345 (for tenant: callwaiting_demo)")
    print("🔑 Test API Key: test_key_67890 (for tenant: test_tenant)")
    print("🎵 Using Microsoft Edge TTS with high-quality neural voices")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
