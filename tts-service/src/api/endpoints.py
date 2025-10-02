"""
FastAPI Endpoints for TTS Microservice
Provides streaming synthesis, voice management, and health monitoring
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File, Form
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import json
import os
import uuid

from .auth import (
    get_current_tenant, 
    check_rate_limit_dependency, 
    require_permission,
    limiter
)
from ..models.coqui_xtts import CoquiXTTSModel
from ..streaming.audio_streamer import AudioStreamer, StreamingMetrics
from ..tenancy.voice_manager import VoiceManager
from ..utils.ssml_parser import SSMLParser
from ..utils.monitoring import MetricsCollector
from ..utils.usage_logger import usage_logger
from ..utils.storage_backend import storage_backend

logger = logging.getLogger(__name__)

# Configuration
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

# Initialize FastAPI app
app = FastAPI(
    title="CallWaiting.ai TTS Service",
    description="High-performance TTS microservice using Coqui XTTS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
tts_model = CoquiXTTSModel()
voice_manager = VoiceManager()
audio_streamer = AudioStreamer()
ssml_parser = SSMLParser()
metrics = MetricsCollector()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize TTS model on startup"""
    try:
        await tts_model.initialize()
        logger.info("🚀 TTS Service started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize TTS model: {e}")
        raise

@app.get("/v1/health")
async def health_check():
    """Health check endpoint with detailed status"""
    model_info = tts_model.get_model_info()
    
    return {
        "status": "healthy" if model_info["initialized"] else "degraded",
        "timestamp": time.time(),
        "version": "1.0.0",
        "model": model_info,
        "uptime": time.time() - metrics.start_time,
        "memory_usage": metrics.get_memory_usage(),
        "active_streams": audio_streamer.get_buffer_status()["buffer_size"]
    }

@app.post("/v1/synthesize")
@limiter.limit("1000/minute")
async def synthesize_text(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en"),
    ssml: Optional[str] = Form(None),
    streaming: bool = Form(True),
    tenant_info: Dict[str, Any] = Depends(get_current_tenant),
    rate_limit_info: Dict[str, Any] = Depends(check_rate_limit_dependency)
):
    """
    Synthesize text to speech with streaming support
    
    Args:
        text: Text to synthesize
        voice_id: Voice identifier
        language: Language code
        ssml: Optional SSML markup
        streaming: Enable streaming response
    """
    start_time = time.time()
    tenant_id = tenant_info["tenant_id"]
    
    try:
        # Get voice configuration
        voice_config = await voice_manager.get_voice_config(tenant_id, voice_id)
        if not voice_config:
            raise HTTPException(
                status_code=404, 
                detail=f"Voice '{voice_id}' not found for tenant"
            )
        
        # Parse SSML if provided
        if ssml:
            parsed_text = ssml_parser.parse(ssml)
        else:
            parsed_text = text
        
        # Record metrics
        metrics.record_synthesis_request(tenant_id, len(parsed_text))
        
        if streaming:
            # Streaming response
            async def generate_audio():
                streaming_metrics = StreamingMetrics()
                streaming_metrics.start()
                
                try:
                    async for chunk in tts_model.synthesize_streaming(
                        text=parsed_text,
                        voice_id=voice_id,
                        language=voice_config["language"],
                        reference_audio=voice_config.get("reference_audio_path")
                    ):
                        streaming_metrics.record_chunk(len(chunk))
                        yield chunk
                        
                except Exception as e:
                    logger.error(f"Error in streaming synthesis: {e}")
                    raise HTTPException(status_code=500, detail=str(e))
                finally:
                    # Record final metrics
                    final_metrics = streaming_metrics.get_metrics()
                    latency_ms = int((time.time() - start_time) * 1000)
                    metrics.record_synthesis_complete(
                        tenant_id, 
                        time.time() - start_time,
                        final_metrics
                    )
                    # Log to Supabase
                    await usage_logger.log_synthesis(
                        tenant_id=tenant_id,
                        input_chars=len(parsed_text),
                        audio_bytes=final_metrics.get("total_bytes", 0),
                        latency_ms=latency_ms,
                        streaming=True,
                        voice_id=voice_id,
                        language=language,
                        endpoint="synthesize"
                    )
            
            return StreamingResponse(
                generate_audio(),
                media_type="audio/wav",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-Voice-ID": voice_id,
                    "X-Streaming": "true"
                }
            )
        else:
            # Batch response
            audio_data = await tts_model.synthesize_batch(
                text=parsed_text,
                voice_id=voice_id,
                language=voice_config["language"],
                reference_audio=voice_config.get("reference_audio_path")
            )
            
            # Record metrics
            latency_ms = int((time.time() - start_time) * 1000)
            metrics.record_synthesis_complete(tenant_id, time.time() - start_time)
            
            # Log to Supabase
            await usage_logger.log_synthesis(
                tenant_id=tenant_id,
                input_chars=len(parsed_text),
                audio_bytes=len(audio_data),
                latency_ms=latency_ms,
                streaming=False,
                voice_id=voice_id,
                language=language,
                endpoint="synthesize"
            )
            
            return StreamingResponse(
                iter([audio_data]),
                media_type="audio/wav",
                headers={
                    "X-Tenant-ID": tenant_id,
                    "X-Voice-ID": voice_id,
                    "X-Streaming": "false"
                }
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in synthesis: {e}")
        metrics.record_synthesis_error(tenant_id, str(e))
        # Log error to Supabase
        await usage_logger.log_synthesis(
            tenant_id=tenant_id,
            input_chars=len(text),
            audio_bytes=0,
            latency_ms=int((time.time() - start_time) * 1000),
            streaming=streaming,
            voice_id=voice_id,
            language=language,
            endpoint="synthesize",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/synthesize-url")
@limiter.limit("1000/minute")
async def synthesize_to_url(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form("default"),
    language: str = Form("en"),
    ssml: Optional[str] = Form(None),
    tenant_info: Dict[str, Any] = Depends(get_current_tenant),
    rate_limit_info: Dict[str, Any] = Depends(check_rate_limit_dependency)
):
    """
    Generate audio and return a URL to download it.

    Note: Uses local storage by default (AUDIO_STORAGE_DIR). For production,
    front with a gateway or replace with S3/Supabase Storage for signed URLs.
    """
    start_time = time.time()
    tenant_id = tenant_info["tenant_id"]

    try:
        # Resolve voice configuration
        voice_config = await voice_manager.get_voice_config(tenant_id, voice_id)
        if not voice_config:
            raise HTTPException(
                status_code=404,
                detail=f"Voice '{voice_id}' not found for tenant"
            )

        # Parse SSML if provided
        parsed_text = ssml_parser.parse(ssml) if ssml else text

        # Record metrics (request)
        metrics.record_synthesis_request(tenant_id, len(parsed_text))

        # Batch synthesize to bytes (WAV default)
        audio_data = await tts_model.synthesize_batch(
            text=parsed_text,
            voice_id=voice_id,
            language=voice_config["language"],
            reference_audio=voice_config.get("reference_audio_path")
        )

        # Save to storage backend (Supabase or local)
        file_id = f"{uuid.uuid4().hex}.wav"
        success, url_or_path = await storage_backend.save_audio(
            file_id=file_id,
            audio_data=audio_data,
            tenant_id=tenant_id,
            content_type="audio/wav"
        )

        if not success:
            raise HTTPException(
                status_code=500,
                detail="Failed to save audio file to storage"
            )

        # Complete metrics
        latency_ms = int((time.time() - start_time) * 1000)
        metrics.record_synthesis_complete(tenant_id, time.time() - start_time)

        # Log to Supabase
        await usage_logger.log_synthesis(
            tenant_id=tenant_id,
            request_id=file_id,
            input_chars=len(parsed_text),
            audio_bytes=len(audio_data),
            latency_ms=latency_ms,
            streaming=False,
            voice_id=voice_id,
            language=language,
            endpoint="synthesize-url",
            metadata={
                "file_id": file_id,
                "storage_backend": "supabase" if storage_backend.is_using_supabase() else "local"
            }
        )

        # Build final URL
        if storage_backend.is_using_supabase():
            # Supabase returns signed URL directly
            url = url_or_path
        else:
            # Local storage: combine with PUBLIC_BASE_URL if provided
            if PUBLIC_BASE_URL:
                url = PUBLIC_BASE_URL.rstrip("/") + url_or_path
            else:
                url = url_or_path

        return {
            "tenant_id": tenant_id,
            "voice_id": voice_id,
            "url": url,
            "content_type": "audio/wav",
            "storage_backend": "supabase" if storage_backend.is_using_supabase() else "local"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in synthesize-url: {e}")
        metrics.record_synthesis_error(tenant_id, str(e))
        # Log error to Supabase
        await usage_logger.log_synthesis(
            tenant_id=tenant_id,
            input_chars=len(text),
            audio_bytes=0,
            latency_ms=int((time.time() - start_time) * 1000),
            streaming=False,
            voice_id=voice_id,
            language=language,
            endpoint="synthesize-url",
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/audio/{tenant_id}/{file_id}")
async def get_audio_file(
    tenant_id: str,
    file_id: str,
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """
    Serve previously generated audio by file_id (local storage only).
    Note: When using Supabase Storage, signed URLs are returned directly.
    """
    # Only used for local storage backend
    if storage_backend.is_using_supabase():
        raise HTTPException(
            status_code=400,
            detail="Direct file serving not available with Supabase Storage. Use signed URLs."
        )
    
    file_path = storage_backend.get_local_file_path(tenant_id, file_id)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return FileResponse(file_path, media_type="audio/wav")

@app.get("/v1/voices")
async def get_voices(
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """Get available voices for tenant"""
    tenant_id = tenant_info["tenant_id"]
    
    try:
        voices = await voice_manager.get_tenant_voices(tenant_id)
        return {
            "tenant_id": tenant_id,
            "voices": voices,
            "total_count": len(voices)
        }
    except Exception as e:
        logger.error(f"Error getting voices: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/v1/voices/upload")
@limiter.limit("10/minute")
async def upload_voice(
    request: Request,
    voice_id: str = Form(...),
    name: str = Form(...),
    description: str = Form(""),
    language: str = Form("en"),
    audio_file: UploadFile = File(...),
    tenant_info: Dict[str, Any] = Depends(require_permission("upload"))
):
    """Upload reference audio for voice cloning"""
    tenant_id = tenant_info["tenant_id"]
    
    try:
        # Validate audio file
        if not audio_file.content_type.startswith("audio/"):
            raise HTTPException(
                status_code=400, 
                detail="File must be an audio file"
            )
        
        # Read audio data
        audio_data = await audio_file.read()
        
        # Create voice profile
        voice_profile = await voice_manager.create_voice_profile(
            tenant_id=tenant_id,
            voice_id=voice_id,
            name=name,
            description=description,
            language=language,
            reference_audio_data=audio_data
        )
        
        return {
            "message": "Voice profile created successfully",
            "voice_profile": voice_profile
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading voice: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.delete("/v1/voices/{voice_id}")
async def delete_voice(
    voice_id: str,
    tenant_info: Dict[str, Any] = Depends(require_permission("upload"))
):
    """Delete a custom voice profile"""
    tenant_id = tenant_info["tenant_id"]
    
    try:
        success = await voice_manager.delete_voice_profile(tenant_id, voice_id)
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Voice '{voice_id}' not found"
            )
        
        return {"message": f"Voice '{voice_id}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting voice: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/tenant/stats")
async def get_tenant_stats(
    tenant_info: Dict[str, Any] = Depends(get_current_tenant)
):
    """Get tenant statistics and usage metrics"""
    tenant_id = tenant_info["tenant_id"]
    
    try:
        voice_stats = await voice_manager.get_tenant_stats(tenant_id)
        usage_stats = metrics.get_tenant_metrics(tenant_id)
        
        return {
            "tenant_id": tenant_id,
            "voice_stats": voice_stats,
            "usage_stats": usage_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting tenant stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/v1/metrics")
async def get_metrics(
    tenant_info: Dict[str, Any] = Depends(require_permission("admin"))
):
    """Get system-wide metrics (admin only)"""
    try:
        return {
            "system_metrics": metrics.get_system_metrics(),
            "model_info": tts_model.get_model_info(),
            "streaming_status": audio_streamer.get_buffer_status()
        }
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return {
        "error": {
            "code": exc.status_code,
            "message": exc.detail,
            "timestamp": time.time()
        }
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": {
            "code": 500,
            "message": "Internal server error",
            "timestamp": time.time()
        }
    }
