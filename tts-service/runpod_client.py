#!/usr/bin/env python3
"""
RunPod TTS Service Client
Client for calling the TTS service deployed on RunPod
"""

import requests
import json
import base64
import time
from typing import Dict, Any, Optional
import os

class RunPodTTSClient:
    """Client for RunPod TTS Service"""
    
    def __init__(self, endpoint_id: str, api_key: str = None):
        self.endpoint_id = endpoint_id
        self.api_key = api_key or os.getenv('RUNPOD_API_KEY')
        self.base_url = f"https://api.runpod.ai/v2/{endpoint_id}"
        
        self.headers = {
            "Content-Type": "application/json",
            "User-Agent": "CallWaiting.ai-TTS-Client/1.0.0"
        }
        
        if self.api_key:
            self.headers["Authorization"] = f"Bearer {self.api_key}"
    
    def synthesize(self, text: str, voice_id: str = "default", language: str = "en") -> Optional[bytes]:
        """Synthesize text to speech"""
        try:
            payload = {
                "input": {
                    "text": text,
                    "voice_id": voice_id,
                    "language": language
                }
            }
            
            print(f"🎤 Sending TTS request to RunPod: '{text[:50]}...'")
            
            response = requests.post(
                f"{self.base_url}/runsync",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "COMPLETED":
                output = result.get("output", {})
                if output.get("status") == "success":
                    audio_base64 = output.get("audio_base64")
                    if audio_base64:
                        audio_data = base64.b64decode(audio_base64)
                        print(f"✅ TTS synthesis successful: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        print("❌ No audio data in response")
                        return None
                else:
                    print(f"❌ TTS synthesis failed: {output.get('error', 'Unknown error')}")
                    return None
            else:
                print(f"❌ RunPod request failed: {result.get('error', 'Unknown error')}")
                return None
                
        except Exception as e:
            print(f"❌ Client error: {e}")
            return None
    
    def synthesize_async(self, text: str, voice_id: str = "default", language: str = "en") -> str:
        """Start async TTS synthesis and return job ID"""
        try:
            payload = {
                "input": {
                    "text": text,
                    "voice_id": voice_id,
                    "language": language
                }
            }
            
            print(f"🎤 Starting async TTS request: '{text[:50]}...'")
            
            response = requests.post(
                f"{self.base_url}/run",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            job_id = result.get("id")
            if job_id:
                print(f"✅ Async job started: {job_id}")
                return job_id
            else:
                print(f"❌ Failed to start async job: {result}")
                return None
                
        except Exception as e:
            print(f"❌ Async request error: {e}")
            return None
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of async job"""
        try:
            response = requests.get(
                f"{self.base_url}/status/{job_id}",
                headers=self.headers,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"❌ Status check error: {e}")
            return {"error": str(e)}
    
    def wait_for_completion(self, job_id: str, timeout: int = 300) -> Optional[bytes]:
        """Wait for async job to complete and return audio data"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_job_status(job_id)
            
            if status.get("status") == "COMPLETED":
                output = status.get("output", {})
                if output.get("status") == "success":
                    audio_base64 = output.get("audio_base64")
                    if audio_base64:
                        audio_data = base64.b64decode(audio_base64)
                        print(f"✅ Async TTS completed: {len(audio_data)} bytes")
                        return audio_data
                else:
                    print(f"❌ Async TTS failed: {output.get('error', 'Unknown error')}")
                    return None
            elif status.get("status") == "FAILED":
                print(f"❌ Async job failed: {status.get('error', 'Unknown error')}")
                return None
            
            time.sleep(2)  # Wait 2 seconds before checking again
        
        print(f"❌ Async job timeout after {timeout} seconds")
        return None

def main():
    """Example usage of RunPod TTS client"""
    print("🎤 RunPod TTS Service Client")
    print("=" * 40)
    
    # Get endpoint ID from environment or user input
    endpoint_id = os.getenv('RUNPOD_ENDPOINT_ID')
    if not endpoint_id:
        endpoint_id = input("Enter your RunPod endpoint ID: ")
    
    # Initialize client
    client = RunPodTTSClient(endpoint_id)
    
    # Test synchronous synthesis
    print("\n🎤 Testing synchronous synthesis...")
    test_text = "Hello, this is a test of the RunPod TTS service using Microsoft Edge TTS."
    
    audio_data = client.synthesize(test_text, voice_id="default")
    if audio_data:
        filename = "runpod_test_sync.mp3"
        with open(filename, 'wb') as f:
            f.write(audio_data)
        print(f"✅ Audio saved to: {filename}")
    else:
        print("❌ Synchronous synthesis failed")
    
    # Test asynchronous synthesis
    print("\n🎤 Testing asynchronous synthesis...")
    job_id = client.synthesize_async(test_text, voice_id="professional")
    if job_id:
        audio_data = client.wait_for_completion(job_id)
        if audio_data:
            filename = "runpod_test_async.mp3"
            with open(filename, 'wb') as f:
                f.write(audio_data)
            print(f"✅ Async audio saved to: {filename}")
        else:
            print("❌ Asynchronous synthesis failed")
    else:
        print("❌ Failed to start async job")
    
    print("\n✅ RunPod TTS client test completed!")

if __name__ == "__main__":
    main()
