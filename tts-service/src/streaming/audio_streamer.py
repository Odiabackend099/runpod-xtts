"""
Audio Streaming Module
Handles buffered streaming, backpressure control, and chunk management
"""

import asyncio
import time
from typing import AsyncGenerator, Optional, Callable
from collections import deque
import logging

logger = logging.getLogger(__name__)

class AudioStreamer:
    """High-performance audio streaming with backpressure control"""
    
    def __init__(self, buffer_size: int = 8192, chunk_size: int = 1024):
        self.buffer_size = buffer_size
        self.chunk_size = chunk_size
        self.buffer = deque(maxlen=buffer_size)
        self.is_streaming = False
        self.backpressure_threshold = buffer_size * 0.8
        
    async def stream_audio(
        self, 
        audio_generator: AsyncGenerator[bytes, None],
        on_chunk: Optional[Callable[[bytes], None]] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream audio with backpressure control
        
        Args:
            audio_generator: Async generator producing audio chunks
            on_chunk: Optional callback for each chunk
            
        Yields:
            Audio chunks with backpressure control
        """
        self.is_streaming = True
        
        try:
            async for chunk in audio_generator:
                if not self.is_streaming:
                    break
                
                # Check backpressure
                if len(self.buffer) > self.backpressure_threshold:
                    logger.warning("Backpressure detected, pausing briefly")
                    await asyncio.sleep(0.01)  # Brief pause
                
                # Add to buffer
                self.buffer.append(chunk)
                
                # Yield chunk
                if on_chunk:
                    on_chunk(chunk)
                yield chunk
                
        except Exception as e:
            logger.error(f"Error in audio streaming: {e}")
            raise
        finally:
            self.is_streaming = False
    
    def stop_streaming(self):
        """Stop the streaming process"""
        self.is_streaming = False
    
    def get_buffer_status(self) -> dict:
        """Get current buffer status"""
        return {
            "buffer_size": len(self.buffer),
            "max_buffer_size": self.buffer_size,
            "is_streaming": self.is_streaming,
            "backpressure_active": len(self.buffer) > self.backpressure_threshold
        }

class StreamingMetrics:
    """Track streaming performance metrics"""
    
    def __init__(self):
        self.start_time = None
        self.chunks_sent = 0
        self.bytes_sent = 0
        self.first_chunk_time = None
        self.last_chunk_time = None
    
    def start(self):
        """Start timing"""
        self.start_time = time.time()
    
    def record_chunk(self, chunk_size: int):
        """Record a chunk being sent"""
        current_time = time.time()
        
        if self.first_chunk_time is None:
            self.first_chunk_time = current_time
        
        self.chunks_sent += 1
        self.bytes_sent += chunk_size
        self.last_chunk_time = current_time
    
    def get_metrics(self) -> dict:
        """Get current metrics"""
        if not self.start_time:
            return {}
        
        current_time = time.time()
        total_time = current_time - self.start_time
        
        metrics = {
            "total_time": total_time,
            "chunks_sent": self.chunks_sent,
            "bytes_sent": self.bytes_sent,
            "chunks_per_second": self.chunks_sent / total_time if total_time > 0 else 0,
            "bytes_per_second": self.bytes_sent / total_time if total_time > 0 else 0
        }
        
        if self.first_chunk_time:
            metrics["time_to_first_chunk"] = self.first_chunk_time - self.start_time
        
        return metrics
