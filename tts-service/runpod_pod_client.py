#!/usr/bin/env python3
"""
RunPod Pod TTS Service Client
Client for calling the TTS service deployed on your RunPod pod
"""

import requests
import json
import time
from typing import Dict, Any, Optional
import os

class RunPodPodTTSClient:
    """Client for RunPod Pod TTS Service"""
    
    def __init__(self, pod_ip: str, port: int = 8000, api_key: str = "cw_demo_12345"):
        self.pod_ip = pod_ip
        self.port = port
        self.api_key = api_key
        self.base_url = f"http://{pod_ip}:{port}"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CallWaiting.ai-TTS-Pod-Client/1.0.0"
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Check if the TTS service is healthy"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/health",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "status": "unhealthy"}
    
    def list_voices(self) -> Dict[str, Any]:
        """List available voices"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/voices",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def synthesize(self, text: str, voice_id: str = "default", language: str = "en") -> Optional[bytes]:
        """Synthesize text to speech"""
        try:
            payload = {
                "text": text,
                "voice_id": voice_id,
                "language": language
            }
            
            print(f"🎤 Sending TTS request to RunPod pod: '{text[:50]}...'")
            
            response = requests.post(
                f"{self.base_url}/v1/synthesize",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            
            # Check if response is JSON (error) or binary (audio)
            content_type = response.headers.get('content-type', '')
            if 'application/json' in content_type:
                result = response.json()
                if 'error' in result:
                    print(f"❌ TTS synthesis failed: {result['error']}")
                    return None
                else:
                    print(f"✅ TTS synthesis successful: {result}")
                    return result
            else:
                # Binary audio data
                audio_data = response.content
                print(f"✅ TTS synthesis successful: {len(audio_data)} bytes")
                return audio_data
                
        except Exception as e:
            print(f"❌ Client error: {e}")
            return None
    
    def synthesize_streaming(self, text: str, voice_id: str = "default", language: str = "en") -> Optional[bytes]:
        """Synthesize text to speech with streaming"""
        try:
            payload = {
                "text": text,
                "voice_id": voice_id,
                "language": language
            }
            
            print(f"🌊 Sending streaming TTS request: '{text[:50]}...'")
            
            response = requests.post(
                f"{self.base_url}/v1/synthesize/streaming",
                headers=self.headers,
                json=payload,
                timeout=60,
                stream=True
            )
            
            response.raise_for_status()
            
            # Collect streaming audio data
            audio_chunks = []
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    audio_chunks.append(chunk)
            
            audio_data = b''.join(audio_chunks)
            print(f"✅ Streaming TTS completed: {len(audio_data)} bytes")
            return audio_data
                
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            return None
    
    def generate_demo_audio(self) -> Dict[str, Any]:
        """Generate demo audio files"""
        try:
            response = requests.post(
                f"{self.base_url}/v1/generate-demo-audio",
                headers=self.headers,
                timeout=120
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_tenant_stats(self) -> Dict[str, Any]:
        """Get tenant statistics"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/tenant/stats",
                headers=self.headers,
                timeout=10
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}

def main():
    """Example usage of RunPod Pod TTS client"""
    print("🎤 RunPod Pod TTS Service Client")
    print("=" * 40)
    
    # Get pod IP from environment or user input
    pod_ip = os.getenv('RUNPOD_POD_IP')
    if not pod_ip:
        pod_ip = input("Enter your RunPod pod IP address: ")
    
    # Initialize client
    client = RunPodPodTTSClient(pod_ip)
    
    # Test health check
    print("\n🏥 Testing health check...")
    health = client.health_check()
    if "error" in health:
        print(f"❌ Health check failed: {health['error']}")
        return
    else:
        print(f"✅ Service is healthy: {health}")
    
    # Test voice listing
    print("\n🎵 Testing voice listing...")
    voices = client.list_voices()
    if "error" in voices:
        print(f"❌ Voice listing failed: {voices['error']}")
    else:
        print(f"✅ Available voices: {voices}")
    
    # Test synthesis
    print("\n🎤 Testing TTS synthesis...")
    test_text = "Hello, this is a test of the RunPod pod TTS service using Microsoft Edge TTS."
    
    audio_data = client.synthesize(test_text, voice_id="default")
    if audio_data:
        filename = "runpod_pod_test.mp3"
        with open(filename, 'wb') as f:
            f.write(audio_data)
        print(f"✅ Audio saved to: {filename}")
    else:
        print("❌ TTS synthesis failed")
    
    # Test streaming synthesis
    print("\n🌊 Testing streaming TTS...")
    audio_data = client.synthesize_streaming(test_text, voice_id="professional")
    if audio_data:
        filename = "runpod_pod_streaming_test.mp3"
        with open(filename, 'wb') as f:
            f.write(audio_data)
        print(f"✅ Streaming audio saved to: {filename}")
    else:
        print("❌ Streaming TTS failed")
    
    # Test demo audio generation
    print("\n🎬 Testing demo audio generation...")
    demo_result = client.generate_demo_audio()
    if "error" in demo_result:
        print(f"❌ Demo generation failed: {demo_result['error']}")
    else:
        print(f"✅ Demo audio generated: {demo_result}")
    
    # Test tenant stats
    print("\n📊 Testing tenant stats...")
    stats = client.get_tenant_stats()
    if "error" in stats:
        print(f"❌ Stats failed: {stats['error']}")
    else:
        print(f"✅ Tenant stats: {stats}")
    
    print("\n✅ RunPod pod TTS client test completed!")

if __name__ == "__main__":
    main()
