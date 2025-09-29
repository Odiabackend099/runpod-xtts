#!/usr/bin/env python3
"""
Direct Audio Generation Script
Generates real audio using Coqui XTTS without web server
"""

import os
import sys
import time
from pathlib import Path

# Set TTS license agreement
os.environ["TTS_AGREE_TO_CPML"] = "1"

try:
    from TTS.api import TTS
    print("✅ TTS imported successfully")
except ImportError as e:
    print(f"❌ Failed to import TTS: {e}")
    sys.exit(1)

def generate_audio(text, output_file="callwaiting_tts_output.wav", voice="default"):
    """Generate real audio using Coqui XTTS"""
    
    print(f"🚀 Starting TTS audio generation...")
    print(f"📝 Text: '{text}'")
    print(f"🎤 Voice: {voice}")
    print(f"📁 Output: {output_file}")
    
    try:
        # Load XTTS model
        print("🔄 Loading XTTS model...")
        start_time = time.time()
        
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.2f} seconds")
        
        # Generate audio
        print("🎤 Generating audio...")
        synthesis_start = time.time()
        
        tts.tts_to_file(
            text=text,
            file_path=output_file,
            language="en"
        )
        
        synthesis_time = time.time() - synthesis_start
        print(f"✅ Audio generated in {synthesis_time:.2f} seconds")
        
        # Check file size
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            print(f"📊 Output file size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            
            # Get audio duration (approximate)
            duration = len(text) * 0.1  # Rough estimate: 10 chars per second
            print(f"⏱️  Estimated duration: {duration:.1f} seconds")
            
            return True
        else:
            print("❌ Output file not created")
            return False
            
    except Exception as e:
        print(f"❌ Error generating audio: {e}")
        return False

def main():
    """Main function to generate audio"""
    
    # Test texts for different durations
    test_texts = [
        {
            "text": "Hello, this is CallWaiting.ai TTS service. We provide high-quality voice synthesis for your business needs.",
            "file": "callwaiting_intro.wav",
            "description": "Short introduction (5-7 seconds)"
        },
        {
            "text": "Welcome to CallWaiting.ai, your premier telecommunications solution. Our advanced TTS technology delivers natural-sounding voices with Nigerian accents, perfect for customer service, IVR systems, and automated messaging. Experience the future of voice technology today.",
            "file": "callwaiting_detailed.wav", 
            "description": "Detailed description (10-12 seconds)"
        },
        {
            "text": "Thank you for calling CallWaiting.ai. Your call is important to us. Please hold while we connect you to the next available representative. Our average wait time is less than two minutes. For immediate assistance, you can also visit our website at www.callwaiting.ai or send us an email at support@callwaiting.ai. We appreciate your patience and look forward to serving you.",
            "file": "callwaiting_hold_message.wav",
            "description": "Hold message (15-18 seconds)"
        }
    ]
    
    print("🎉 CallWaiting.ai TTS Audio Generation")
    print("=" * 50)
    
    success_count = 0
    
    for i, test in enumerate(test_texts, 1):
        print(f"\n📝 Test {i}: {test['description']}")
        print("-" * 30)
        
        if generate_audio(test["text"], test["file"]):
            success_count += 1
            print(f"✅ Successfully generated: {test['file']}")
        else:
            print(f"❌ Failed to generate: {test['file']}")
    
    print(f"\n🎯 Summary: {success_count}/{len(test_texts)} audio files generated successfully")
    
    if success_count > 0:
        print("\n🎵 Generated audio files:")
        for test in test_texts:
            if os.path.exists(test["file"]):
                size = os.path.getsize(test["file"])
                print(f"   📁 {test['file']} ({size:,} bytes)")
        
        print(f"\n🎧 You can play these files with any audio player!")
        print(f"📂 Files are located in: {os.getcwd()}")
    
    return success_count > 0

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Audio generation completed successfully!")
        else:
            print("\n❌ Audio generation failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Audio generation interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
