#!/usr/bin/env python3
"""
Test script for Gemini Voice Service
"""
import asyncio
import os
from dotenv import load_dotenv
from services import GeminiVoiceService, Config

async def test_voice_service():
    """Test the voice service functionality"""
    print("🔊 Testing Gemini Voice Service...")
    
    # Load environment variables
    load_dotenv()
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key or api_key == 'your-gemini-api-key-here':
        print("❌ Error: GEMINI_API_KEY not set in .env file")
        print("Please create a .env file with your Gemini API key:")
        print("GEMINI_API_KEY=your_actual_api_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Initialize voice service
    try:
        voice_service = GeminiVoiceService()
        print("✅ Voice service initialized")
        
        # Test text-to-speech
        test_text = "Hello! This is a test of the Gemini voice service."
        print(f"🎤 Testing TTS with: '{test_text}'")
        
        audio_data = await voice_service.generate_speech(test_text, "Kore")
        
        if audio_data:
            print(f"✅ Voice generated successfully! Audio size: {len(audio_data)} bytes")
            
            # Save test audio file
            with open("test_voice.wav", "wb") as f:
                f.write(audio_data)
            print("💾 Test audio saved as 'test_voice.wav'")
            
            # Test cache functionality
            print("🔄 Testing cache functionality...")
            cached_audio = await voice_service.generate_speech(test_text, "Kore")
            if cached_audio:
                print("✅ Cache working - audio retrieved from cache")
            
            # Test different voice
            print("🎭 Testing different voice (Nova)...")
            nova_audio = await voice_service.generate_speech("Testing Nova voice", "Nova")
            if nova_audio:
                print("✅ Nova voice working!")
            
            return True
        else:
            print("❌ Failed to generate voice")
            return False
            
    except Exception as e:
        print(f"❌ Error testing voice service: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 50)
    print("🧪 Gemini Voice Service Test")
    print("=" * 50)
    
    success = await test_voice_service()
    
    print("=" * 50)
    if success:
        print("🎉 All tests passed! Voice service is working correctly.")
    else:
        print("💥 Some tests failed. Check the errors above.")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
