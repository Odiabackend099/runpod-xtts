"""
Main Server Entry Point
FastAPI application with all endpoints and middleware
"""

import os
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .api.endpoints import app as api_app
from .utils.monitoring import MetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global metrics collector
metrics = MetricsCollector()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("🚀 Starting CallWaiting.ai TTS Service")
    logger.info("📡 Service will be available at: http://localhost:8000")
    logger.info("🔍 Health check: http://localhost:8000/health")
    logger.info("🎤 TTS endpoint: POST http://localhost:8000/v1/synthesize")
    logger.info("📚 API docs: http://localhost:8000/docs")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down TTS Service")

# Create main FastAPI app
app = FastAPI(
    title="CallWaiting.ai TTS Service",
    description="High-performance TTS microservice using Coqui XTTS",
    version="1.0.0",
    lifespan=lifespan
)

# Include API routes
app.include_router(api_app.router, prefix="/api")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "CallWaiting.ai TTS Service",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/v1/health",
            "synthesize": "/v1/synthesize",
            "voices": "/v1/voices",
            "upload_voice": "/v1/voices/upload",
            "tenant_stats": "/v1/tenant/stats",
            "metrics": "/v1/metrics",
            "docs": "/docs"
        },
        "features": [
            "High-quality neural voice synthesis",
            "Streaming audio generation",
            "Multi-tenant voice management",
            "Voice cloning support",
            "SSML markup support",
            "Rate limiting and authentication",
            "Real-time monitoring"
        ]
    }

if __name__ == "__main__":
    # Configuration
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    workers = int(os.getenv("WORKERS", 1))
    reload = os.getenv("RELOAD", "false").lower() == "true"
    
    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Workers: {workers}, Reload: {reload}")
    
    # Run server
    uvicorn.run(
        "src.server:app",
        host=host,
        port=port,
        workers=workers if not reload else 1,
        reload=reload,
        log_level="info"
    )
