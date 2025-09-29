#!/usr/bin/env python3
"""
Test client for CallWaiting.ai TTS Service
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "cw_demo_12345"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_voices():
    """Test voices endpoint"""
    print("\n🎵 Testing voices endpoint...")
    response = requests.get(f"{BASE_URL}/voices", headers=HEADERS)
    print(f"Status: {response.status_code}")
    voices = response.json()
    print(f"Available voices: {len(voices['voices'])}")
    for voice in voices['voices']:
        print(f"  - {voice['id']}: {voice['name']}")
    return response.status_code == 200

def test_synthesis():
    """Test text synthesis"""
    print("\n🎤 Testing text synthesis...")
    
    test_cases = [
        {"text": "Hello, this is a test", "voice_id": "default"},
        {"text": "Welcome to CallWaiting.ai", "voice_id": "naija_female"},
        {"text": "This is a longer test message to see how the TTS service handles more complex text.", "voice_id": "professional"}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n  Test {i}: {test_case['text'][:30]}... (voice: {test_case['voice_id']})")
        
        response = requests.post(
            f"{BASE_URL}/synthesize",
            headers=HEADERS,
            data=test_case
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            audio_size = len(response.content)
            print(f"  ✅ Audio generated: {audio_size} bytes")
            
            # Save audio file
            filename = f"test_audio_{i}_{test_case['voice_id']}.mp3"
            with open(filename, 'wb') as f:
                f.write(response.content)
            print(f"  💾 Saved as: {filename}")
        else:
            print(f"  ❌ Error: {response.text}")
    
    return True

def test_tenant_stats():
    """Test tenant stats endpoint"""
    print("\n📊 Testing tenant stats...")
    response = requests.get(f"{BASE_URL}/tenant/stats", headers=HEADERS)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"Tenant: {stats['tenant_name']} ({stats['tenant_id']})")
        print(f"Requests: {stats['requests_count']}")
        print(f"Uptime: {stats['uptime']:.2f} seconds")
    return response.status_code == 200

def main():
    """Run all tests"""
    print("🚀 Starting CallWaiting.ai TTS Service Tests")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("List Voices", test_voices),
        ("Text Synthesis", test_synthesis),
        ("Tenant Stats", test_tenant_stats)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📋 Test Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! TTS service is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the service logs.")

if __name__ == "__main__":
    main()
