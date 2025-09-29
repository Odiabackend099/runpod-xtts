#!/usr/bin/env python3
"""
Test Runner for CallWaiting.ai TTS Service
Provides easy commands to run different test suites
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and display results"""
    print(f"\n🧪 {description}")
    print(f"Running: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
        else:
            print(f"❌ {description} - FAILED (exit code: {result.returncode})")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 CallWaiting.ai TTS Service - Test Runner")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
    else:
        test_type = "all"
    
    success = True
    
    if test_type in ["all", "health"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestHealthAndRootEndpoints", "-v"],
            "Health & Root Endpoints Tests"
        )
    
    if test_type in ["all", "auth"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestAuthentication", "-v"],
            "Authentication Tests"
        )
    
    if test_type in ["all", "voice"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestVoiceManagement", "-v"],
            "Voice Management Tests"
        )
    
    if test_type in ["all", "audio"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestAudioSynthesis", "-v"],
            "Audio Synthesis Tests"
        )
    
    if test_type in ["all", "tenant"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestTenantManagement", "-v"],
            "Tenant Management Tests"
        )
    
    if test_type in ["all", "error"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestErrorHandling", "-v"],
            "Error Handling Tests"
        )
    
    if test_type in ["all", "manager"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestTTSManager", "-v"],
            "TTS Manager Tests"
        )
    
    if test_type in ["all", "performance"]:
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py::TestPerformance", "-v"],
            "Performance Tests"
        )
    
    if test_type == "all":
        success &= run_command(
            ["python3", "-m", "pytest", "tests/test_streaming_tts_service.py", "-v", "--durations=10"],
            "Complete Test Suite"
        )
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED!")
        print("✅ TTS Service is ready for production")
    else:
        print("⚠️  SOME TESTS FAILED")
        print("🔧 Check the output above for details")
    
    print("\n📊 Test Report: TEST_REPORT.md")
    print("🚀 Service URL: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    main()
