"""
Storage backend for audio files with support for local storage and Supabase Storage.
Provides signed URLs for public access without authentication.
"""
import os
import logging
from typing import Optional, Tuple
from datetime import timedelta

try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover
    create_client = None
    Client = None

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "tts-audio")
LOCAL_STORAGE_DIR = os.getenv("AUDIO_STORAGE_DIR") or os.getenv("AUDIO_STORAGE_PATH") or "/tmp/tts-audio"
STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "local")  # "local" or "supabase"
SIGNED_URL_EXPIRY_SECONDS = int(os.getenv("SIGNED_URL_EXPIRY_SECONDS", "3600"))  # 1 hour default


class StorageBackend:
    """Abstract storage backend for audio files."""
    
    def __init__(self):
        self.backend = STORAGE_BACKEND
        self.supabase_client: Optional[Client] = None
        self.local_storage_dir = LOCAL_STORAGE_DIR
        
        # Initialize based on backend choice
        if self.backend == "supabase" and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and create_client:
            try:
                self.supabase_client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                # Test storage access
                self.supabase_client.storage.list_buckets()
                logger.info(f"✅ Supabase Storage backend initialized (bucket: {SUPABASE_STORAGE_BUCKET})")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase Storage, falling back to local: {e}")
                self.backend = "local"
        
        # Ensure local directory exists (fallback or primary)
        if self.backend == "local":
            os.makedirs(self.local_storage_dir, exist_ok=True)
            logger.info(f"✅ Local storage backend initialized (dir: {self.local_storage_dir})")
    
    async def save_audio(
        self,
        file_id: str,
        audio_data: bytes,
        tenant_id: str,
        content_type: str = "audio/wav"
    ) -> Tuple[bool, Optional[str]]:
        """
        Save audio file to storage backend.
        
        Args:
            file_id: Unique file identifier
            audio_data: Audio file bytes
            tenant_id: Tenant identifier (for organizing files)
            content_type: MIME type
        
        Returns:
            Tuple of (success, signed_url or local_path)
        """
        if self.backend == "supabase" and self.supabase_client:
            return await self._save_to_supabase(file_id, audio_data, tenant_id, content_type)
        else:
            return await self._save_to_local(file_id, audio_data, tenant_id)
    
    async def _save_to_supabase(
        self,
        file_id: str,
        audio_data: bytes,
        tenant_id: str,
        content_type: str
    ) -> Tuple[bool, Optional[str]]:
        """Save to Supabase Storage and return signed URL."""
        try:
            # Organize by tenant for easier management
            storage_path = f"{tenant_id}/{file_id}"
            
            # Upload to Supabase Storage
            result = self.supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
                path=storage_path,
                file=audio_data,
                file_options={"content-type": content_type, "upsert": "true"}
            )
            
            if not result:
                logger.error(f"Failed to upload to Supabase Storage: {storage_path}")
                return False, None
            
            # Generate signed URL (expires in configured seconds)
            signed_url_response = self.supabase_client.storage.from_(SUPABASE_STORAGE_BUCKET).create_signed_url(
                path=storage_path,
                expires_in=SIGNED_URL_EXPIRY_SECONDS
            )
            
            if not signed_url_response or 'signedURL' not in signed_url_response:
                logger.error(f"Failed to generate signed URL for: {storage_path}")
                return False, None
            
            signed_url = signed_url_response['signedURL']
            logger.info(f"✅ Uploaded to Supabase Storage: {storage_path}")
            return True, signed_url
            
        except Exception as e:
            logger.error(f"❌ Supabase Storage error: {e}", exc_info=True)
            return False, None
    
    async def _save_to_local(
        self,
        file_id: str,
        audio_data: bytes,
        tenant_id: str
    ) -> Tuple[bool, Optional[str]]:
        """Save to local filesystem and return relative path."""
        try:
            # Create tenant subdirectory
            tenant_dir = os.path.join(self.local_storage_dir, tenant_id)
            os.makedirs(tenant_dir, exist_ok=True)
            
            file_path = os.path.join(tenant_dir, file_id)
            
            with open(file_path, "wb") as f:
                f.write(audio_data)
            
            # Return relative path (to be combined with PUBLIC_BASE_URL)
            relative_path = f"/v1/audio/{tenant_id}/{file_id}"
            logger.info(f"✅ Saved to local storage: {file_path}")
            return True, relative_path
            
        except Exception as e:
            logger.error(f"❌ Local storage error: {e}", exc_info=True)
            return False, None
    
    def get_local_file_path(self, tenant_id: str, file_id: str) -> str:
        """Get local file path for serving."""
        return os.path.join(self.local_storage_dir, tenant_id, file_id)
    
    def is_using_supabase(self) -> bool:
        """Check if using Supabase Storage backend."""
        return self.backend == "supabase"


# Global singleton instance
storage_backend = StorageBackend()
