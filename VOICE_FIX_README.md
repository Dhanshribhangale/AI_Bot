# Voice Generation Fix for AI Bot

## Problem
The original code was getting the error: "Unknown field for GenerateContentRequest: config" because it was using an outdated Google AI API structure.

## Solution
Updated the code to use the new Google GenAI API (`google-genai` library) with the correct structure for Gemini 2.5 Flash Preview TTS.

## Changes Made

### 1. Updated Dependencies
- Changed from `google-generativeai` to `google-genai`
- Updated requirements.txt

### 2. Fixed API Calls
- Updated `GeminiVoiceService.generate_speech()` to use the correct API structure
- Updated `GeminiClient.generate_response()` to use the new API
- Updated `GeminiClient.smart_summarize()` to use the new API

### 3. Correct API Structure
The voice generation now uses the correct API call:
```python
response = client.models.generate_content(
    model="gemini-2.5-flash-preview-tts",
    contents=text,
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name,
                )
            )
        ),
    )
)
```

### 4. Model Configuration
- TTS Model: `gemini-2.5-flash-preview-tts`
- Chat Model: `gemini-2.0-flash-exp`

## Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API Key
Create a `.env` file with:
```
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Test Voice Generation
```bash
python test_voice_new_api.py
```

This will:
- Test voice generation with the new API
- Save a test audio file as `test_voice_new_api.wav`
- Test cache functionality
- Show cache statistics

## Expected Results
- ✅ Voice generation should work without the "config" error
- ✅ Audio files should be generated successfully
- ✅ Cache functionality should work
- ✅ No more API structure errors

## Troubleshooting
If you still get errors:
1. Make sure you have the latest `google-genai` library
2. Verify your API key is valid
3. Check that the model name is correct
4. Ensure you have access to the Gemini 2.5 Flash Preview TTS model

## Files Modified
- `services.py` - Updated API calls
- `config.py` - Updated TTS model
- `requirements.txt` - Updated dependencies
- `client.py` - Fixed imports and method signatures
- `main.py` - Fixed imports
- Removed `server.py` (duplicate classes)

The voice generation system should now work correctly with the new Google GenAI API!
