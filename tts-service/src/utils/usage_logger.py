"""
Usage logging module for tracking TTS requests in Supabase.
Logs synthesis requests for analytics, billing, and monitoring.
"""
import os
import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from supabase import create_client, Client
except Exception:  # pragma: no cover
    create_client = None
    Client = None

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
USAGE_LOGS_TABLE = os.getenv("SUPABASE_USAGE_LOGS_TABLE", "usage_logs")


def _is_configured() -> bool:
    """Check if Supabase is configured for usage logging."""
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY and create_client is not None)


class UsageLogger:
    """Logs TTS usage events to Supabase for analytics and billing."""
    
    def __init__(self) -> None:
        self.enabled: bool = _is_configured()
        self.client: Optional[Client] = None
        if self.enabled:
            try:
                self.client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
                logger.info("✅ Usage logger initialized with Supabase")
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase usage logger: {e}")
                self.enabled = False
        else:
            logger.info("⚠️ Usage logger disabled (Supabase not configured)")
    
    async def log_synthesis(
        self,
        tenant_id: str,
        request_id: Optional[str] = None,
        input_chars: int = 0,
        audio_bytes: int = 0,
        latency_ms: int = 0,
        streaming: bool = False,
        voice_id: str = "default",
        language: str = "en",
        error: Optional[str] = None,
        endpoint: str = "synthesize",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log a synthesis request to Supabase.
        
        Args:
            tenant_id: Tenant/user identifier
            request_id: Unique request ID (generated if not provided)
            input_chars: Number of input characters
            audio_bytes: Size of generated audio in bytes
            latency_ms: Request latency in milliseconds
            streaming: Whether request used streaming
            voice_id: Voice identifier used
            language: Language code
            error: Error message if request failed
            endpoint: API endpoint used (synthesize, synthesize-url)
            metadata: Additional metadata (JSONB)
        
        Returns:
            True if logged successfully, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            request_id = request_id or str(uuid.uuid4())
            
            log_entry = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "request_id": request_id,
                "input_chars": input_chars,
                "audio_bytes": audio_bytes,
                "latency_ms": latency_ms,
                "streaming": streaming,
                "voice_id": voice_id,
                "language": language,
                "endpoint": endpoint,
                "error": error,
                "metadata": metadata or {},
                "created_at": datetime.utcnow().isoformat()
            }
            
            # Insert into usage_logs table
            result = self.client.table(USAGE_LOGS_TABLE).insert(log_entry).execute()
            
            # Check if insert was successful
            if result.data:
                logger.debug(f"✅ Logged usage for tenant {tenant_id}: {request_id}")
                return True
            else:
                logger.warning(f"⚠️ Usage log insert returned no data for {request_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to log usage: {e}", exc_info=True)
            return False
    
    async def log_voice_operation(
        self,
        tenant_id: str,
        operation: str,  # upload, delete, update
        voice_id: str,
        voice_name: Optional[str] = None,
        file_size_bytes: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log voice management operations (upload, delete, etc.).
        
        Args:
            tenant_id: Tenant identifier
            operation: Operation type (upload, delete, update)
            voice_id: Voice identifier
            voice_name: Human-readable voice name
            file_size_bytes: Size of uploaded audio file
            metadata: Additional metadata
        
        Returns:
            True if logged successfully, False otherwise
        """
        if not self.enabled or not self.client:
            return False
        
        try:
            log_entry = {
                "id": str(uuid.uuid4()),
                "tenant_id": tenant_id,
                "request_id": f"voice_{operation}_{uuid.uuid4().hex[:8]}",
                "input_chars": 0,
                "audio_bytes": file_size_bytes or 0,
                "latency_ms": 0,
                "streaming": False,
                "voice_id": voice_id,
                "language": "",
                "endpoint": f"voice_{operation}",
                "error": None,
                "metadata": {
                    **(metadata or {}),
                    "operation": operation,
                    "voice_name": voice_name
                },
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table(USAGE_LOGS_TABLE).insert(log_entry).execute()
            
            if result.data:
                logger.debug(f"✅ Logged voice {operation} for tenant {tenant_id}: {voice_id}")
                return True
            else:
                logger.warning(f"⚠️ Voice operation log returned no data")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to log voice operation: {e}", exc_info=True)
            return False
    
    async def get_tenant_usage_summary(
        self,
        tenant_id: str,
        days: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Get usage summary for a tenant over specified time period.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back
        
        Returns:
            Dictionary with usage statistics or None if error
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Calculate date filter (simplified - in production use proper date math)
            # This is a basic example; real implementation would use proper date filtering
            result = (
                self.client
                .table(USAGE_LOGS_TABLE)
                .select("*")
                .eq("tenant_id", tenant_id)
                .limit(1000)  # Cap for safety
                .execute()
            )
            
            if not result.data:
                return {
                    "tenant_id": tenant_id,
                    "total_requests": 0,
                    "total_chars": 0,
                    "total_bytes": 0,
                    "error_count": 0
                }
            
            logs = result.data
            
            return {
                "tenant_id": tenant_id,
                "total_requests": len(logs),
                "total_chars": sum(log.get("input_chars", 0) for log in logs),
                "total_bytes": sum(log.get("audio_bytes", 0) for log in logs),
                "error_count": sum(1 for log in logs if log.get("error")),
                "streaming_requests": sum(1 for log in logs if log.get("streaming")),
                "voice_usage": self._count_by_field(logs, "voice_id"),
                "endpoint_usage": self._count_by_field(logs, "endpoint")
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get usage summary: {e}", exc_info=True)
            return None
    
    @staticmethod
    def _count_by_field(logs: list, field: str) -> Dict[str, int]:
        """Helper to count occurrences by field."""
        counts: Dict[str, int] = {}
        for log in logs:
            value = log.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts


# Global singleton instance
usage_logger = UsageLogger()
