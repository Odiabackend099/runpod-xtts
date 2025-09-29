#!/usr/bin/env python3
"""
Simple Audio Generation using Coqui TTS
Direct approach without complex dependencies
"""

import os
import sys
import time
import subprocess

# Set TTS license agreement
os.environ["TTS_AGREE_TO_CPML"] = "1"

def generate_audio_with_tts_cli(text, output_file="callwaiting_output.wav"):
    """Generate audio using TTS CLI directly"""
    
    print(f"🎤 Generating audio with Coqui TTS...")
    print(f"📝 Text: '{text}'")
    print(f"📁 Output: {output_file}")
    
    try:
        # Use TTS CLI to generate audio
        cmd = [
            "python3", "-m", "TTS.bin.synthesize",
            "--text", text,
            "--model_name", "tts_models/multilingual/multi-dataset/xtts_v2",
            "--language_idx", "en",
            "--out_path", output_file
        ]
        
        print(f"🔄 Running command: {' '.join(cmd)}")
        start_time = time.time()
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        generation_time = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Audio generated successfully in {generation_time:.2f} seconds")
            
            # Check if file was created
            if os.path.exists(output_file):
                file_size = os.path.getsize(output_file)
                print(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                return True
            else:
                print("❌ Output file not found")
                return False
        else:
            print(f"❌ TTS command failed:")
            print(f"   Return code: {result.returncode}")
            print(f"   Error: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ TTS generation timed out (5 minutes)")
        return False
    except Exception as e:
        print(f"❌ Error running TTS: {e}")
        return False

def generate_audio_with_python_api():
    """Generate audio using Python API with minimal imports"""
    
    print("🎤 Generating audio with Python API...")
    
    try:
        # Try to import and use TTS
        from TTS.api import TTS
        
        print("✅ TTS imported successfully")
        
        # Load model
        print("🔄 Loading XTTS model...")
        start_time = time.time()
        
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=True)
        
        load_time = time.time() - start_time
        print(f"✅ Model loaded in {load_time:.2f} seconds")
        
        # Test texts
        test_texts = [
            "Hello, this is CallWaiting.ai TTS service. We provide high-quality voice synthesis.",
            "Welcome to CallWaiting.ai, your premier telecommunications solution with advanced TTS technology.",
            "Thank you for calling CallWaiting.ai. Your call is important to us. Please hold while we connect you."
        ]
        
        success_count = 0
        
        for i, text in enumerate(test_texts, 1):
            output_file = f"callwaiting_audio_{i}.wav"
            print(f"\n📝 Generating audio {i}: '{text[:50]}...'")
            
            try:
                synthesis_start = time.time()
                tts.tts_to_file(
                    text=text,
                    file_path=output_file,
                    language="en"
                )
                synthesis_time = time.time() - synthesis_start
                
                if os.path.exists(output_file):
                    file_size = os.path.getsize(output_file)
                    print(f"✅ Generated {output_file} in {synthesis_time:.2f}s ({file_size:,} bytes)")
                    success_count += 1
                else:
                    print(f"❌ Failed to create {output_file}")
                    
            except Exception as e:
                print(f"❌ Error generating audio {i}: {e}")
        
        print(f"\n🎯 Summary: {success_count}/{len(test_texts)} audio files generated")
        return success_count > 0
        
    except ImportError as e:
        print(f"❌ Failed to import TTS: {e}")
        return False
    except Exception as e:
        print(f"❌ Error with Python API: {e}")
        return False

def main():
    """Main function"""
    
    print("🎉 CallWaiting.ai TTS Audio Generation")
    print("=" * 50)
    
    # Try Python API first
    print("\n🔄 Attempting Python API approach...")
    if generate_audio_with_python_api():
        print("\n✅ Python API approach successful!")
        return True
    
    # Fallback to CLI approach
    print("\n🔄 Attempting CLI approach...")
    test_text = "Hello, this is CallWaiting.ai TTS service providing high-quality voice synthesis."
    
    if generate_audio_with_tts_cli(test_text):
        print("\n✅ CLI approach successful!")
        return True
    
    print("\n❌ Both approaches failed")
    return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Audio generation completed!")
            print("🎧 Check the generated .wav files in the current directory")
        else:
            print("\n❌ Audio generation failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️  Audio generation interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)
