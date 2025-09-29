#!/usr/bin/env python3
"""
TTS Manager for CallWaiting.ai
Handles API key validation, voice model management, and streaming inference
"""

import os
import sys
import time
import hashlib
import tempfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

# Add Coqui TTS to path
coqui_path = Path(__file__).parent.parent.parent / "coqui-tts"
sys.path.insert(0, str(coqui_path))

logger = logging.getLogger(__name__)

@dataclass
class VoiceProfile:
    """Voice profile data structure"""
    voice_id: str
    name: str
    tenant_id: str
    created_at: str
    reference_audio_path: Optional[str] = None
    speaker_embedding: Optional[Any] = None
    gpt_cond_latent: Optional[Any] = None
    language: str = "en"

@dataclass
class TenantInfo:
    """Tenant information"""
    tenant_id: str
    api_key: str
    name: str
    rate_limit_per_minute: int = 100
    max_voices: int = 10
    created_at: str = ""

class TTSManager:
    """Manages TTS models, voice profiles, and API authentication"""
    
    def __init__(self):
        self.voice_profiles: Dict[str, Dict[str, VoiceProfile]] = {}  # tenant_id -> voice_id -> profile
        self.tenants: Dict[str, TenantInfo] = {}
        self.tts_model = None
        self.model_loaded = False
        self._initialize_default_tenants()
        self._load_tts_model()
    
    def _initialize_default_tenants(self):
        """Initialize default tenants for testing"""
        default_tenants = [
            {
                "tenant_id": "callwaiting_demo",
                "api_key": "cw_demo_12345",
                "name": "CallWaiting Demo",
                "rate_limit_per_minute": 1000,
                "max_voices": 20
            },
            {
                "tenant_id": "test_tenant",
                "api_key": "test_key_67890", 
                "name": "Test Tenant",
                "rate_limit_per_minute": 100,
                "max_voices": 5
            }
        ]
        
        for tenant_data in default_tenants:
            tenant = TenantInfo(
                tenant_id=tenant_data["tenant_id"],
                api_key=tenant_data["api_key"],
                name=tenant_data["name"],
                rate_limit_per_minute=tenant_data["rate_limit_per_minute"],
                max_voices=tenant_data["max_voices"],
                created_at=datetime.now().isoformat()
            )
            self.tenants[tenant.tenant_id] = tenant
            self.voice_profiles[tenant.tenant_id] = {}
        
        logger.info(f"✅ Initialized {len(self.tenants)} default tenants")
    
    def _load_tts_model(self):
        """Load the Coqui XTTS model"""
        try:
            logger.info("🚀 Loading Coqui XTTS model...")
            
            # Set environment variable for license agreement
            os.environ["TTS_AGREE_TO_CPML"] = "1"
            
            from TTS.api import TTS
            
            # Load XTTS model
            self.tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
            self.model_loaded = True
            
            logger.info("✅ Coqui XTTS model loaded successfully!")
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to load Coqui XTTS: {e}")
            self.model_loaded = False
    
    def validate_api_key(self, tenant_id: str, api_key: str) -> bool:
        """Validate API key for tenant"""
        if tenant_id not in self.tenants:
            return False
        
        tenant = self.tenants[tenant_id]
        return tenant.api_key == api_key
    
    def get_tenant_info(self, tenant_id: str) -> Optional[TenantInfo]:
        """Get tenant information"""
        return self.tenants.get(tenant_id)
    
    def get_voice_model(self, tenant_id: str, voice_id: str) -> Optional[VoiceProfile]:
        """Get voice profile for tenant and voice_id"""
        if tenant_id not in self.voice_profiles:
            return None
        
        return self.voice_profiles[tenant_id].get(voice_id)
    
    def list_voice_profiles(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all voice profiles for a tenant"""
        if tenant_id not in self.voice_profiles:
            return []
        
        profiles = []
        for voice_id, profile in self.voice_profiles[tenant_id].items():
            profiles.append({
                "voice_id": profile.voice_id,
                "name": profile.name,
                "created_at": profile.created_at,
                "language": profile.language,
                "has_reference_audio": profile.reference_audio_path is not None
            })
        
        return profiles
    
    def create_voice_profile(
        self, 
        tenant_id: str, 
        name: str, 
        audio_bytes: bytes,
        language: str = "en"
    ) -> Optional[VoiceProfile]:
        """Create a new voice profile from reference audio"""
        if not self.model_loaded:
            logger.error("❌ TTS model not loaded - cannot create voice profile")
            return None
        
        if tenant_id not in self.tenants:
            logger.error(f"❌ Invalid tenant_id: {tenant_id}")
            return None
        
        tenant = self.tenants[tenant_id]
        if len(self.voice_profiles[tenant_id]) >= tenant.max_voices:
            logger.error(f"❌ Tenant {tenant_id} has reached max voices limit")
            return None
        
        try:
            # Generate unique voice_id
            voice_id = f"{tenant_id}_{name}_{int(time.time())}"
            voice_id = hashlib.md5(voice_id.encode()).hexdigest()[:12]
            
            # Save reference audio to temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                reference_audio_path = temp_file.name
            
            # Create voice profile
            profile = VoiceProfile(
                voice_id=voice_id,
                name=name,
                tenant_id=tenant_id,
                created_at=datetime.now().isoformat(),
                reference_audio_path=reference_audio_path,
                language=language
            )
            
            # Store profile
            self.voice_profiles[tenant_id][voice_id] = profile
            
            logger.info(f"✅ Created voice profile: {voice_id} for tenant: {tenant_id}")
            return profile
            
        except Exception as e:
            logger.error(f"❌ Failed to create voice profile: {e}")
            return None
    
    async def inference_stream(
        self, 
        text: str, 
        voice_profile: VoiceProfile,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio inference using Coqui XTTS"""
        if not self.model_loaded or not self.tts_model:
            raise RuntimeError("TTS model not loaded")
        
        try:
            logger.info(f"🎤 Starting streaming inference for voice: {voice_profile.voice_id}")
            
            # For XTTS, we need to use the reference audio for voice cloning
            if voice_profile.reference_audio_path and os.path.exists(voice_profile.reference_audio_path):
                # Use voice cloning with reference audio
                logger.info("🔄 Using voice cloning with reference audio")
                
                # Generate audio with voice cloning
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
                    self.tts_model.tts_to_file(
                        text=text,
                        file_path=temp_output.name,
                        speaker_wav=voice_profile.reference_audio_path,
                        language=language
                    )
                    
                    # Stream the generated audio file in chunks
                    with open(temp_output.name, 'rb') as f:
                        while True:
                            chunk = f.read(1024)  # 1KB chunks
                            if not chunk:
                                break
                            yield chunk
                    
                    # Cleanup
                    os.unlink(temp_output.name)
            else:
                # Use default voice
                logger.info("🔄 Using default XTTS voice")
                
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_output:
                    self.tts_model.tts_to_file(
                        text=text,
                        file_path=temp_output.name,
                        language=language
                    )
                    
                    # Stream the generated audio file in chunks
                    with open(temp_output.name, 'rb') as f:
                        while True:
                            chunk = f.read(1024)  # 1KB chunks
                            if not chunk:
                                break
                            yield chunk
                    
                    # Cleanup
                    os.unlink(temp_output.name)
            
            logger.info("✅ Streaming inference completed")
            
        except Exception as e:
            logger.error(f"❌ Streaming inference failed: {e}")
            raise RuntimeError(f"Streaming inference failed: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded TTS model"""
        return {
            "model_loaded": self.model_loaded,
            "model_name": "xtts_v2" if self.model_loaded else None,
            "supported_languages": ["en", "es", "fr", "de", "it", "pt", "pl", "tr", "ru", "nl", "cs", "ar", "zh-cn", "ja", "hu", "ko"] if self.model_loaded else [],
            "voice_cloning_supported": self.model_loaded,
            "streaming_supported": self.model_loaded
        }
    
    def cleanup(self):
        """Cleanup resources"""
        # Clean up temporary reference audio files
        for tenant_id, profiles in self.voice_profiles.items():
            for voice_id, profile in profiles.items():
                if profile.reference_audio_path and os.path.exists(profile.reference_audio_path):
                    try:
                        os.unlink(profile.reference_audio_path)
                    except Exception as e:
                        logger.warning(f"Failed to cleanup {profile.reference_audio_path}: {e}")

# Global TTS Manager instance
tts_manager = TTSManager()
