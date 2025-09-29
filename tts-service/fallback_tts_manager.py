#!/usr/bin/env python3
"""
Fallback TTS Manager for CallWaiting.ai
Provides system TTS fallback when Coqui XTTS is not available
"""

import os
import sys
import time
import hashlib
import tempfile
import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
import asyncio
import json

logger = logging.getLogger(__name__)

@dataclass
class VoiceProfile:
    """Voice profile data structure"""
    voice_id: str
    name: str
    tenant_id: str
    created_at: str
    reference_audio_path: Optional[str] = None
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

class FallbackTTSManager:
    """Fallback TTS Manager using system TTS when Coqui XTTS is not available"""
    
    def __init__(self):
        self.voice_profiles: Dict[str, Dict[str, VoiceProfile]] = {}  # tenant_id -> voice_id -> profile
        self.tenants: Dict[str, TenantInfo] = {}
        self.model_loaded = False  # Always False for fallback
        self._initialize_default_tenants()
        self._create_default_voices()
    
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
    
    def _create_default_voices(self):
        """Create default voice profiles for each tenant"""
        for tenant_id in self.tenants.keys():
            # Create default voice
            default_voice = VoiceProfile(
                voice_id="default",
                name="Default System Voice",
                tenant_id=tenant_id,
                created_at=datetime.now().isoformat(),
                language="en"
            )
            self.voice_profiles[tenant_id]["default"] = default_voice
            
            # Create Nigerian voice
            naija_voice = VoiceProfile(
                voice_id="naija_female",
                name="Nigerian Female Voice",
                tenant_id=tenant_id,
                created_at=datetime.now().isoformat(),
                language="en"
            )
            self.voice_profiles[tenant_id]["naija_female"] = naija_voice
            
            # Create male voice
            male_voice = VoiceProfile(
                voice_id="naija_male",
                name="Nigerian Male Voice", 
                tenant_id=tenant_id,
                created_at=datetime.now().isoformat(),
                language="en"
            )
            self.voice_profiles[tenant_id]["naija_male"] = male_voice
        
        logger.info("✅ Created default voice profiles for all tenants")
    
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
        """Create a new voice profile from reference audio (stored for future use)"""
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
    
    def _get_voice_settings(self, voice_id: str) -> Dict[str, str]:
        """Get voice settings for system TTS based on voice_id"""
        voice_settings = {
            "default": {"voice": "Alex", "rate": "200", "format": "aiff"},
            "naija_female": {"voice": "Samantha", "rate": "180", "format": "aiff"},
            "naija_male": {"voice": "Daniel", "rate": "190", "format": "aiff"}
        }
        return voice_settings.get(voice_id, voice_settings["default"])
    
    async def inference_stream(
        self, 
        text: str, 
        voice_profile: VoiceProfile,
        language: str = "en"
    ) -> AsyncGenerator[bytes, None]:
        """Stream audio inference using system TTS"""
        try:
            logger.info(f"🎤 Starting system TTS inference for voice: {voice_profile.voice_id}")
            
            # Get voice settings
            voice_settings = self._get_voice_settings(voice_profile.voice_id)
            
            # Create temporary file for output with proper format
            file_format = voice_settings.get("format", "aiff")
            with tempfile.NamedTemporaryFile(suffix=f'.{file_format}', delete=False) as temp_file:
                temp_path = temp_file.name
            
            # Generate audio using system TTS (macOS say command)
            cmd = [
                "say", 
                "-v", voice_settings["voice"],
                "-r", voice_settings["rate"],
                "-o", temp_path,
                "--file-format", file_format.upper(),
                text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                raise RuntimeError(f"System TTS failed: {result.stderr}")
            
            if not os.path.exists(temp_path):
                raise RuntimeError("Audio file was not created")
            
            # Stream the generated audio file in chunks
            with open(temp_path, 'rb') as f:
                while True:
                    chunk = f.read(1024)  # 1KB chunks
                    if not chunk:
                        break
                    yield chunk
            
            # Cleanup
            os.unlink(temp_path)
            
            logger.info("✅ System TTS inference completed")
            
        except Exception as e:
            logger.error(f"❌ System TTS inference failed: {e}")
            raise RuntimeError(f"System TTS inference failed: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the TTS system"""
        return {
            "model_loaded": False,  # Always False for fallback
            "model_name": "system_tts_fallback",
            "supported_languages": ["en"],
            "voice_cloning_supported": False,
            "streaming_supported": True,
            "fallback_mode": True,
            "system_tts": "macOS say command"
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

# Global Fallback TTS Manager instance
fallback_tts_manager = FallbackTTSManager()
