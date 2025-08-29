#!/usr/bin/env python3
"""
Simple test script to verify voice generation works without pyaudio
"""

import asyncio
import logging
import os
from services import GeminiVoiceService
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_voice_generation():
    """Test voice generation with the new API calls"""
    
    if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY == 'your-gemini-api-key-here':
        logger.error("Please set GEMINI_API_KEY in your .env file")
        return False
    
    # Set the API key as environment variable for the new library
    os.environ['GOOGLE_API_KEY'] = Config.GEMINI_API_KEY
    
    voice_service = GeminiVoiceService()
    
    # Test text
    test_text = "Hello! This is a test of the voice generation system."
    
    try:
        logger.info(f"Testing voice generation with text: {test_text}")
        logger.info(f"Using TTS model: {Config.TTS_MODEL}")
        
        # Generate speech
        audio_data = await voice_service.generate_speech(test_text, "Kore")
        
        if audio_data:
            logger.info(f"✅ Voice generation successful! Generated {len(audio_data)} bytes of audio data")
            
            # Save test audio file
            with open("test_voice_simple.wav", "wb") as f:
                f.write(audio_data)
            logger.info("💾 Test audio saved as 'test_voice_simple.wav'")
            
            return True
        else:
            logger.error("❌ Voice generation failed - no audio data returned")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during voice generation test: {e}")
        return False

async def main():
    """Main test function"""
    print("🎤 Simple Voice Generation Test")
    print("=" * 40)
    
    success = await test_voice_generation()
    
    if success:
        print("\n✅ Voice generation test passed!")
        print("The voice system is working correctly.")
    else:
        print("\n❌ Voice generation test failed.")
        print("Please check the error messages above.")
    
    print("\n" + "=" * 40)

if __name__ == "__main__":
    asyncio.run(main())
