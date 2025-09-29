#!/usr/bin/env python3
"""
CallWaiting.ai TTS Service Client
Simple client for calling the local TTS service
"""

import requests
import json
import time
from typing import Dict, Any, Optional, Generator
from client_config import get_config

class TTSServiceClient:
    """Client for CallWaiting.ai TTS Service"""
    
    def __init__(self, config=None):
        self.config = config or get_config()
        self.session = requests.Session()
        self.session.headers.update(self.config.HEADERS)
        
    def health_check(self) -> Dict[str, Any]:
        """Check if TTS service is healthy"""
        try:
            response = self.session.get(
                self.config.ENDPOINTS['health'],
                timeout=self.config.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def get_voices(self) -> Dict[str, Any]:
        """Get available voices"""
        try:
            response = self.session.get(
                self.config.ENDPOINTS['voices'],
                timeout=self.config.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def synthesize(self, text: str, voice_id: str = None, language: str = None) -> Optional[bytes]:
        """Synthesize text to speech"""
        try:
            voice_id = voice_id or self.config.DEFAULT_VOICE
            language = language or self.config.DEFAULT_LANGUAGE
            
            data = {
                'text': text,
                'voice_id': voice_id,
                'language': language
            }
            
            response = self.session.post(
                self.config.ENDPOINTS['synthesize'],
                data=data,
                timeout=self.config.TIMEOUT
            )
            response.raise_for_status()
            return response.content
            
        except Exception as e:
            if self.config.DEBUG:
                print(f"❌ Synthesis failed: {e}")
            return None
    
    def synthesize_to_file(self, text: str, filename: str, voice_id: str = None, language: str = None) -> bool:
        """Synthesize text to speech and save to file"""
        audio_data = self.synthesize(text, voice_id, language)
        if audio_data:
            try:
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                return True
            except Exception as e:
                if self.config.DEBUG:
                    print(f"❌ Failed to save audio: {e}")
                return False
        return False
    
    def synthesize_streaming(self, text: str, voice_id: str = None, language: str = None) -> Generator[bytes, None, None]:
        """Stream audio synthesis"""
        try:
            voice_id = voice_id or self.config.DEFAULT_VOICE
            language = language or self.config.DEFAULT_LANGUAGE
            
            data = {
                'text': text,
                'voice_id': voice_id,
                'language': language
            }
            
            response = self.session.post(
                self.config.ENDPOINTS['streaming'],
                data=data,
                stream=True,
                timeout=self.config.STREAMING_TIMEOUT
            )
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
                    
        except Exception as e:
            if self.config.DEBUG:
                print(f"❌ Streaming synthesis failed: {e}")
            yield b''
    
    def get_tenant_stats(self) -> Dict[str, Any]:
        """Get tenant statistics"""
        try:
            response = self.session.get(
                self.config.ENDPOINTS['tenant_stats'],
                timeout=self.config.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def generate_demo_audio(self) -> Dict[str, Any]:
        """Generate demo audio files"""
        try:
            response = self.session.post(
                self.config.ENDPOINTS['demo_audio'],
                timeout=self.config.TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

def main():
    """Example usage of TTS client"""
    print("🎤 CallWaiting.ai TTS Service Client")
    print("=" * 40)
    
    # Initialize client
    client = TTSServiceClient()
    
    # Health check
    print("🔍 Checking service health...")
    health = client.health_check()
    print(f"Status: {health.get('status', 'unknown')}")
    
    if health.get('status') != 'healthy':
        print("❌ Service is not healthy. Please start the TTS server first.")
        return
    
    # Get available voices
    print("\n🎵 Getting available voices...")
    voices = client.get_voices()
    if 'voices' in voices:
        print(f"Available voices: {len(voices['voices'])}")
        for voice in voices['voices']:
            print(f"  - {voice['id']}: {voice['name']}")
    
    # Test synthesis
    print("\n🎤 Testing text synthesis...")
    test_text = "Hello, this is a test of the CallWaiting.ai TTS service using Microsoft Edge TTS."
    
    audio_data = client.synthesize(test_text, voice_id="default")
    if audio_data:
        print(f"✅ Synthesis successful: {len(audio_data)} bytes")
        
        # Save to file
        filename = "test_synthesis.mp3"
        if client.synthesize_to_file(test_text, filename, voice_id="default"):
            print(f"✅ Audio saved to: {filename}")
    else:
        print("❌ Synthesis failed")
    
    # Test different voices
    print("\n🎭 Testing different voices...")
    test_voices = ["default", "professional", "friendly"]
    
    for voice_id in test_voices:
        filename = f"test_{voice_id}.mp3"
        if client.synthesize_to_file(f"This is a test with the {voice_id} voice.", filename, voice_id=voice_id):
            print(f"✅ Generated {filename}")
        else:
            print(f"❌ Failed to generate {filename}")
    
    # Get tenant stats
    print("\n📊 Getting tenant statistics...")
    stats = client.get_tenant_stats()
    if 'tenant_id' in stats:
        print(f"Tenant: {stats['tenant_id']}")
        print(f"Available voices: {stats.get('available_voices', 0)}")
        print(f"Engine: {stats.get('engine', 'unknown')}")
    
    print("\n✅ TTS client test completed!")

if __name__ == "__main__":
    main()
