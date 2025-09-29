#!/usr/bin/env python3
"""
CallWaiting.ai TTS Service Client Configuration
Environment variables and settings for local TTS service integration
"""

import os
from typing import Dict, Any, Optional

class TTSClientConfig:
    """Configuration class for TTS service client"""
    
    def __init__(self):
        # Server Configuration
        self.HOST = os.getenv('TTS_HOST', 'localhost')
        self.PORT = os.getenv('TTS_PORT', '8000')
        self.BASE_URL = f"http://{self.HOST}:{self.PORT}"
        self.API_VERSION = os.getenv('TTS_API_VERSION', 'v1')
        self.API_BASE = f"{self.BASE_URL}/{self.API_VERSION}"
        
        # Authentication
        self.API_KEY = os.getenv('TTS_API_KEY', 'cw_demo_12345')
        self.API_HEADER = os.getenv('TTS_API_HEADER', 'Authorization')
        self.API_PREFIX = os.getenv('TTS_API_PREFIX', 'Bearer')
        
        # TTS Settings
        self.DEFAULT_VOICE = os.getenv('TTS_DEFAULT_VOICE', 'default')
        self.DEFAULT_LANGUAGE = os.getenv('TTS_DEFAULT_LANGUAGE', 'en')
        self.AUDIO_FORMAT = os.getenv('TTS_AUDIO_FORMAT', 'mp3')
        
        # Available Voices
        self.VOICES = {
            'default': 'en-US-AriaNeural',
            'naija_female': 'en-US-JennyNeural',
            'naija_male': 'en-US-GuyNeural', 
            'professional': 'en-US-DavisNeural',
            'friendly': 'en-US-EmmaNeural',
            'calm': 'en-US-MichelleNeural',
            'energetic': 'en-US-BrianNeural'
        }
        
        # API Endpoints
        self.ENDPOINTS = {
            'health': f"{self.API_BASE}/health",
            'synthesize': f"{self.API_BASE}/synthesize",
            'streaming': f"{self.API_BASE}/synthesize/streaming",
            'voices': f"{self.API_BASE}/voices",
            'tenant_stats': f"{self.API_BASE}/tenant/stats",
            'demo_audio': f"{self.API_BASE}/generate-demo-audio"
        }
        
        # Headers
        self.HEADERS = {
            self.API_HEADER: f"{self.API_PREFIX} {self.API_KEY}",
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'CallWaiting.ai-TTS-Client/1.0.0'
        }
        
        # Timeout settings
        self.TIMEOUT = int(os.getenv('TTS_TIMEOUT', '30'))
        self.STREAMING_TIMEOUT = int(os.getenv('TTS_STREAMING_TIMEOUT', '60'))
        
        # Retry settings
        self.MAX_RETRIES = int(os.getenv('TTS_MAX_RETRIES', '3'))
        self.RETRY_DELAY = float(os.getenv('TTS_RETRY_DELAY', '1.0'))
        
        # Debug settings
        self.DEBUG = os.getenv('TTS_DEBUG', 'false').lower() == 'true'
        self.VERBOSE = os.getenv('TTS_VERBOSE', 'false').lower() == 'true'

# Global configuration instance
config = TTSClientConfig()

def get_config() -> TTSClientConfig:
    """Get the global TTS client configuration"""
    return config

def print_config():
    """Print current configuration"""
    print("🎤 CallWaiting.ai TTS Service Configuration")
    print("=" * 50)
    print(f"Server URL: {config.BASE_URL}")
    print(f"API Base: {config.API_BASE}")
    print(f"API Key: {config.API_KEY[:10]}...")
    print(f"Default Voice: {config.DEFAULT_VOICE}")
    print(f"Available Voices: {len(config.VOICES)}")
    print(f"Timeout: {config.TIMEOUT}s")
    print(f"Debug Mode: {config.DEBUG}")
    print("=" * 50)

if __name__ == "__main__":
    print_config()
