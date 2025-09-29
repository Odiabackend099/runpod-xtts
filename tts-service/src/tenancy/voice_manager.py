"""
Multi-tenant Voice Management
Handles voice profiles, tenant isolation, and voice cloning
"""

import os
import hashlib
import json
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import aiofiles
from sqlalchemy import create_engine, Column, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

logger = logging.getLogger(__name__)

Base = declarative_base()

class VoiceProfile(Base):
    """Voice profile database model"""
    __tablename__ = "voice_profiles"
    
    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False, index=True)
    voice_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    language = Column(String, default="en")
    reference_audio_path = Column(String)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VoiceManager:
    """Multi-tenant voice management system"""
    
    def __init__(self, db_url: str = "sqlite:///voices.db", storage_path: str = "./voice_storage"):
        self.db_url = db_url
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Initialize database
        self.engine = create_engine(db_url)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.Session = Session
        
        # Preloaded voices
        self.preloaded_voices = self._load_preloaded_voices()
    
    def _load_preloaded_voices(self) -> Dict[str, Dict[str, Any]]:
        """Load preloaded voice profiles"""
        return {
            "naija_female": {
                "name": "Nigerian Female",
                "description": "High-quality Nigerian female voice",
                "language": "en",
                "is_preloaded": True
            },
            "naija_male": {
                "name": "Nigerian Male", 
                "description": "High-quality Nigerian male voice",
                "language": "en",
                "is_preloaded": True
            },
            "default": {
                "name": "Default Voice",
                "description": "Default XTTS neural voice",
                "language": "en",
                "is_preloaded": True
            }
        }
    
    async def get_tenant_voices(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all voices available for a tenant"""
        session = self.Session()
        try:
            # Get custom voices from database
            custom_voices = session.query(VoiceProfile).filter(
                VoiceProfile.tenant_id == tenant_id
            ).all()
            
            # Convert to dict format
            voices = []
            for voice in custom_voices:
                voices.append({
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "description": voice.description,
                    "language": voice.language,
                    "is_default": voice.is_default,
                    "is_custom": True,
                    "created_at": voice.created_at.isoformat()
                })
            
            # Add preloaded voices
            for voice_id, voice_data in self.preloaded_voices.items():
                voices.append({
                    "voice_id": voice_id,
                    "name": voice_data["name"],
                    "description": voice_data["description"],
                    "language": voice_data["language"],
                    "is_preloaded": True
                })
            
            return voices
            
        finally:
            session.close()
    
    async def create_voice_profile(
        self, 
        tenant_id: str, 
        voice_id: str, 
        name: str,
        description: str = "",
        language: str = "en",
        reference_audio_data: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """Create a new voice profile for a tenant"""
        session = self.Session()
        try:
            # Check if voice already exists
            existing = session.query(VoiceProfile).filter(
                VoiceProfile.tenant_id == tenant_id,
                VoiceProfile.voice_id == voice_id
            ).first()
            
            if existing:
                raise ValueError(f"Voice {voice_id} already exists for tenant {tenant_id}")
            
            # Store reference audio if provided
            reference_audio_path = None
            if reference_audio_data:
                reference_audio_path = await self._store_reference_audio(
                    tenant_id, voice_id, reference_audio_data
                )
            
            # Create voice profile
            voice_profile = VoiceProfile(
                id=f"{tenant_id}_{voice_id}",
                tenant_id=tenant_id,
                voice_id=voice_id,
                name=name,
                description=description,
                language=language,
                reference_audio_path=reference_audio_path
            )
            
            session.add(voice_profile)
            session.commit()
            
            return {
                "voice_id": voice_id,
                "name": name,
                "description": description,
                "language": language,
                "reference_audio_path": reference_audio_path,
                "created_at": voice_profile.created_at.isoformat()
            }
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def _store_reference_audio(
        self, 
        tenant_id: str, 
        voice_id: str, 
        audio_data: bytes
    ) -> str:
        """Store reference audio file securely"""
        # Create tenant directory
        tenant_dir = self.storage_path / tenant_id
        tenant_dir.mkdir(exist_ok=True)
        
        # Generate secure filename
        filename = f"{voice_id}_{hashlib.sha256(audio_data).hexdigest()[:16]}.wav"
        file_path = tenant_dir / filename
        
        # Write audio data
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(audio_data)
        
        return str(file_path)
    
    async def get_voice_config(
        self, 
        tenant_id: str, 
        voice_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get voice configuration for synthesis"""
        # Check preloaded voices first
        if voice_id in self.preloaded_voices:
            return {
                "voice_id": voice_id,
                "language": self.preloaded_voices[voice_id]["language"],
                "reference_audio_path": None,
                "is_preloaded": True
            }
        
        # Check custom voices
        session = self.Session()
        try:
            voice = session.query(VoiceProfile).filter(
                VoiceProfile.tenant_id == tenant_id,
                VoiceProfile.voice_id == voice_id
            ).first()
            
            if voice:
                return {
                    "voice_id": voice_id,
                    "language": voice.language,
                    "reference_audio_path": voice.reference_audio_path,
                    "is_custom": True
                }
            
            return None
            
        finally:
            session.close()
    
    async def delete_voice_profile(self, tenant_id: str, voice_id: str) -> bool:
        """Delete a voice profile"""
        session = self.Session()
        try:
            voice = session.query(VoiceProfile).filter(
                VoiceProfile.tenant_id == tenant_id,
                VoiceProfile.voice_id == voice_id
            ).first()
            
            if not voice:
                return False
            
            # Delete reference audio file if exists
            if voice.reference_audio_path and os.path.exists(voice.reference_audio_path):
                os.unlink(voice.reference_audio_path)
            
            session.delete(voice)
            session.commit()
            return True
            
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
    
    async def get_tenant_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get statistics for a tenant"""
        session = self.Session()
        try:
            voice_count = session.query(VoiceProfile).filter(
                VoiceProfile.tenant_id == tenant_id
            ).count()
            
            return {
                "tenant_id": tenant_id,
                "custom_voices": voice_count,
                "preloaded_voices": len(self.preloaded_voices),
                "total_voices": voice_count + len(self.preloaded_voices)
            }
            
        finally:
            session.close()
