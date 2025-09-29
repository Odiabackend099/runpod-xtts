#!/bin/bash
# RunPod Setup Script for CallWaiting.ai TTS Service
# Run this script in your RunPod terminal

set -e

echo "🚀 Setting up CallWaiting.ai TTS Service on RunPod"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in RunPod environment
if [[ -z "$RUNPOD_POD_ID" ]]; then
    echo -e "${YELLOW}⚠️  Note: RUNPOD_POD_ID not set. You may not be in a RunPod environment.${NC}"
fi

echo -e "${BLUE}📋 Environment Information:${NC}"
echo "  Current directory: $(pwd)"
echo "  User: $(whoami)"
echo "  Python version: $(python3 --version)"
echo "  Available space:"
df -h .
echo ""

# Step 1: Create workspace directory
echo -e "${YELLOW}📁 Step 1: Setting up workspace...${NC}"
mkdir -p /workspace/tts-service
cd /workspace/tts-service

echo -e "${GREEN}✅ Workspace created at /workspace/tts-service${NC}"

# Step 2: Clone the repository (if you have a git repo)
echo -e "${YELLOW}📥 Step 2: Setting up TTS service files...${NC}"

# Create the main TTS server file
cat > real_tts_server.py << 'EOF'
#!/usr/bin/env python3
"""
CallWaiting.ai TTS Service for RunPod
High-performance Text-to-Speech microservice using Microsoft Edge TTS
"""

import os
import asyncio
import logging
import tempfile
from typing import AsyncGenerator, Dict, Any, Optional, List
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
    "energetic": "en-US-BrianNeural"
}

# Tenant configuration
TENANTS = {
    "cw_demo_12345": {
        "tenant_id": "callwaiting_demo",
        "name": "CallWaiting Demo",
        "rate_limit": 1000,
        "features": ["synthesis", "streaming", "voice_upload"]
    },
    "test_key_67890": {
        "tenant_id": "test_tenant", 
        "name": "Test Tenant",
        "rate_limit": 100,
        "features": ["synthesis", "streaming"]
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
            raise Exception(f"TTS synthesis failed: {str(e)}")

# Initialize TTS manager
tts_manager = RealTTSManager()

# Request tracking
request_stats = defaultdict(lambda: {"count": 0, "total_time": 0, "last_request": None})

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 Starting CallWaiting.ai Real TTS Service")
    logger.info("📡 Service will be available at: http://0.0.0.0:8000")
    logger.info("🎤 Real TTS endpoint: POST http://0.0.0.0:8000/v1/synthesize")
    logger.info("🌊 Streaming endpoint: POST http://0.0.0.0:8000/v1/synthesize/streaming")
    logger.info("📚 API docs: http://0.0.0.0:8000/docs")
    logger.info("🔑 Demo API Key: cw_demo_12345 (for tenant: callwaiting_demo)")
    logger.info("🔑 Test API Key: test_key_67890 (for tenant: test_tenant)")
    logger.info("🎵 Using Microsoft Edge TTS with high-quality neural voices")
    yield
    logger.info("🛑 Shutting down TTS service")

# Create FastAPI app
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

def get_current_tenant(authorization: str = None) -> Dict[str, Any]:
    """Get current tenant from API key"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization format")
    
    api_key = authorization[7:]  # Remove "Bearer " prefix
    
    if api_key not in TENANTS:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return TENANTS[api_key]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "CallWaiting.ai TTS Service",
        "version": "1.0.0",
        "status": "running",
        "engine": "Microsoft Edge TTS",
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
        "service": "CallWaiting.ai TTS Service",
        "engine": "Microsoft Edge TTS",
        "timestamp": time.time(),
        "uptime": time.time(),
        "memory_usage": psutil.virtual_memory().percent,
        "cpu_usage": psutil.cpu_percent(),
        "available_voices": len(EDGE_VOICES)
    }

@app.get("/v1/voices")
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
        ],
        "total": len(EDGE_VOICES)
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
        start_time = time.time()
        
        logger.info(f"🎤 Synthesizing: '{text[:50]}...' with voice '{voice_id}'")
        
        # Generate audio
        audio_data = await tts_manager.synthesize(text, voice_id, language)
        
        # Update stats
        request_stats[tenant_info["tenant_id"]]["count"] += 1
        request_stats[tenant_info["tenant_id"]]["total_time"] += time.time() - start_time
        request_stats[tenant_info["tenant_id"]]["last_request"] = time.time()
        
        logger.info(f"✅ Audio generated: {len(audio_data)} bytes")
        
        return Response(
            content=audio_data,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=tts_output_{voice_id}.mp3",
                "X-TTS-Voice": voice_id,
                "X-TTS-Engine": "Microsoft Edge TTS"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/synthesize/streaming")
async def synthesize_streaming(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en"),
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """Streaming text to speech synthesis"""
    try:
        logger.info(f"🌊 Streaming synthesis: '{text[:50]}...' with voice '{voice_id}'")
        
        async def generate_audio_stream():
            try:
                # Generate audio
                audio_data = await tts_manager.synthesize(text, voice_id, language)
                
                # Stream in chunks
                chunk_size = 8192
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i + chunk_size]
                    yield chunk
                    
            except Exception as e:
                logger.error(f"❌ Streaming error: {e}")
                yield b""
        
        return StreamingResponse(
            generate_audio_stream(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": f"attachment; filename=tts_streaming_{voice_id}.mp3",
                "X-TTS-Voice": voice_id,
                "X-TTS-Engine": "Microsoft Edge TTS"
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Streaming synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/generate-demo-audio")
async def generate_demo_audio(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """Generate demo audio files"""
    try:
        demo_texts = {
            "service_introduction": "Welcome to CallWaiting.ai TTS service. This is a demonstration of our high-quality text-to-speech capabilities using Microsoft Edge TTS.",
            "professional_greeting": "Hello, this is CallWaiting.ai. We provide professional-grade text-to-speech services for your applications.",
            "friendly_message": "Hi there! Thanks for trying out our TTS service. We hope you enjoy the high-quality audio output."
        }
        
        results = {}
        
        for demo_name, text in demo_texts.items():
            try:
                voice_id = "default" if demo_name == "service_introduction" else "professional" if demo_name == "professional_greeting" else "friendly"
                audio_data = await tts_manager.synthesize(text, voice_id)
                
                filename = f"demo_{demo_name}_{tenant_info['tenant_id']}.mp3"
                filepath = f"/workspace/{filename}"
                
                with open(filepath, 'wb') as f:
                    f.write(audio_data)
                
                results[demo_name] = {
                    "filename": filename,
                    "size": len(audio_data),
                    "voice": voice_id,
                    "status": "success"
                }
                
                logger.info(f"✅ Generated {filename} ({len(audio_data)} bytes)")
                
            except Exception as e:
                results[demo_name] = {
                    "error": str(e),
                    "status": "failed"
                }
                logger.error(f"❌ Demo generation failed for {demo_name}: {e}")
        
        return {
            "status": "completed",
            "tenant": tenant_info["tenant_id"],
            "results": results,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"❌ Demo generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/tenant/stats")
async def get_tenant_stats(tenant_info: Dict[str, Any] = Depends(get_current_tenant)):
    """Get tenant statistics"""
    stats = request_stats[tenant_info["tenant_id"]]
    
    return {
        "tenant_id": tenant_info["tenant_id"],
        "tenant_name": tenant_info["name"],
        "total_requests": stats["count"],
        "average_response_time": stats["total_time"] / max(stats["count"], 1),
        "last_request": stats["last_request"],
        "rate_limit": tenant_info["rate_limit"],
        "features": tenant_info["features"],
        "timestamp": time.time()
    }

if __name__ == "__main__":
    uvicorn.run(
        "real_tts_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
EOF

echo -e "${GREEN}✅ TTS server file created${NC}"

# Step 3: Create requirements file
cat > requirements.txt << 'EOF'
# Core TTS Engine
edge-tts>=6.1.0

# Web Framework
fastapi>=0.104.1
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6

# HTTP Client
requests>=2.31.0
httpx>=0.25.0

# System Monitoring
psutil>=5.9.6

# Utilities
pydantic>=2.0.0
typing-extensions>=4.8.0
EOF

echo -e "${GREEN}✅ Requirements file created${NC}"

# Step 4: Install dependencies
echo -e "${YELLOW}📦 Step 3: Installing dependencies...${NC}"
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo -e "${RED}❌ Dependency installation failed${NC}"
    exit 1
fi

# Step 5: Test Edge TTS installation
echo -e "${YELLOW}🧪 Step 4: Testing Edge TTS installation...${NC}"
python3 -c "
import edge_tts
print('✅ Edge TTS installed successfully')
print('✅ Available voices:', len(edge_tts.list_voices()))
"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Edge TTS test passed${NC}"
else
    echo -e "${RED}❌ Edge TTS test failed${NC}"
    exit 1
fi

# Step 6: Create startup script
cat > start_tts_service.sh << 'EOF'
#!/bin/bash
echo "🚀 Starting CallWaiting.ai TTS Service on RunPod"
echo "================================================"
echo "Service will be available at: http://0.0.0.0:8000"
echo "API Documentation: http://0.0.0.0:8000/docs"
echo "Health Check: http://0.0.0.0:8000/v1/health"
echo ""
echo "Demo API Key: cw_demo_12345"
echo "Test API Key: test_key_67890"
echo ""
echo "Starting server..."
python3 real_tts_server.py
EOF

chmod +x start_tts_service.sh

echo -e "${GREEN}✅ Startup script created${NC}"

# Step 7: Create test client
cat > test_tts_service.py << 'EOF'
#!/usr/bin/env python3
"""
Test client for CallWaiting.ai TTS Service on RunPod
"""

import requests
import json
import time

def test_tts_service():
    """Test the TTS service"""
    base_url = "http://localhost:8000"
    api_key = "cw_demo_12345"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    print("🧪 Testing CallWaiting.ai TTS Service")
    print("=" * 40)
    
    # Test 1: Health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/v1/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"   Status: {response.json()['status']}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check error: {e}")
    
    # Test 2: List voices
    print("\n2. Testing voice listing...")
    try:
        response = requests.get(f"{base_url}/v1/voices", headers=headers)
        if response.status_code == 200:
            voices = response.json()
            print(f"✅ Voice listing passed: {voices['total']} voices available")
        else:
            print(f"❌ Voice listing failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Voice listing error: {e}")
    
    # Test 3: Synthesize text
    print("\n3. Testing text synthesis...")
    try:
        data = {
            "text": "Hello, this is a test of the CallWaiting.ai TTS service on RunPod.",
            "voice_id": "default",
            "language": "en"
        }
        response = requests.post(f"{base_url}/v1/synthesize", headers=headers, data=data)
        if response.status_code == 200:
            print(f"✅ Text synthesis passed: {len(response.content)} bytes")
            # Save audio file
            with open("test_output.mp3", "wb") as f:
                f.write(response.content)
            print("   Audio saved to: test_output.mp3")
        else:
            print(f"❌ Text synthesis failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Text synthesis error: {e}")
    
    # Test 4: Tenant stats
    print("\n4. Testing tenant stats...")
    try:
        response = requests.get(f"{base_url}/v1/tenant/stats", headers=headers)
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Tenant stats passed: {stats['total_requests']} requests")
        else:
            print(f"❌ Tenant stats failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Tenant stats error: {e}")
    
    print("\n🎉 TTS service testing completed!")

if __name__ == "__main__":
    test_tts_service()
EOF

chmod +x test_tts_service.py

echo -e "${GREEN}✅ Test client created${NC}"

# Step 8: Final setup
echo -e "${YELLOW}🎯 Step 5: Final setup...${NC}"

# Create audio output directory
mkdir -p /workspace/audio_output

# Set permissions
chmod +x real_tts_server.py
chmod +x test_tts_service.py

echo -e "${GREEN}✅ Setup completed successfully!${NC}"

# Display final information
echo ""
echo -e "${BLUE}🎉 CallWaiting.ai TTS Service Setup Complete!${NC}"
echo ""
echo -e "${BLUE}📋 Service Information:${NC}"
echo "  • Engine: Microsoft Edge TTS"
echo "  • Voices: 7 high-quality neural voices"
echo "  • Port: 8000"
echo "  • API Documentation: http://0.0.0.0:8000/docs"
echo ""
echo -e "${BLUE}🚀 To start the service:${NC}"
echo "  ./start_tts_service.sh"
echo ""
echo -e "${BLUE}🧪 To test the service:${NC}"
echo "  python3 test_tts_service.py"
echo ""
echo -e "${BLUE}🔑 API Keys:${NC}"
echo "  • Demo: cw_demo_12345"
echo "  • Test: test_key_67890"
echo ""
echo -e "${BLUE}📡 Endpoints:${NC}"
echo "  • Health: GET /v1/health"
echo "  • Voices: GET /v1/voices"
echo "  • Synthesize: POST /v1/synthesize"
echo "  • Streaming: POST /v1/synthesize/streaming"
echo "  • Demo Audio: POST /v1/generate-demo-audio"
echo "  • Stats: GET /v1/tenant/stats"
echo ""
echo -e "${GREEN}✅ Ready for API calls!${NC}"
