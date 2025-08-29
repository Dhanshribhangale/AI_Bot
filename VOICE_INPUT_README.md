# 🎤 AI Voice Bot - Voice Input & Output Guide

## Overview
Your AI Voice Bot now supports **voice input** using the Web Speech API! This means you can speak to the bot and it will automatically respond with voice output.

## ✨ New Features

### 🎤 Voice Input
- **Click the microphone button** (🎤) to start voice recording
- **Speak your message** clearly into your microphone
- **Automatic transcription** - see your words appear in real-time
- **Instant AI response** with automatic voice output

### 🔊 Automatic Voice Response
- When you use voice input, the bot **automatically enables voice output**
- AI responses are **automatically converted to speech**
- No need to manually enable voice for each response

## 🚀 How to Use Voice Input

### 1. **Start Voice Input**
   - Click the **🎤 microphone button** in the chat input area
   - The button will turn **yellow** and show **⏹️** while recording
   - You'll see "Listening..." status

### 2. **Speak Your Message**
   - Speak clearly into your microphone
   - Watch your words appear in the input field in real-time
   - The bot will process your speech when you finish

### 3. **Get Voice Response**
   - The AI will respond with text
   - **Automatically** generate voice for the response
   - Voice output is enabled automatically for voice input

## 🎯 Voice Input Workflow

```
🎤 Click Microphone → 🎵 Speak Message → 🤖 AI Processes → 🔊 Voice Response
```

## 🔧 Technical Details

### Browser Compatibility
- **Chrome/Edge**: Full support ✅
- **Firefox**: Limited support ⚠️
- **Safari**: Limited support ⚠️

### Speech Recognition
- Uses **Web Speech API** (no external services needed)
- **Real-time transcription** with interim results
- **Automatic language detection** (English)
- **Error handling** for recognition issues

### Voice Output
- **Automatic voice generation** for voice input responses
- **Voice selection** available (Kore, Nova, Fable, Echo)
- **Audio queue management** for smooth playback

## 🎨 UI Elements

### New Controls
- **🎤 Microphone Button**: Start/stop voice recording
- **Voice Status**: Shows recording status and feedback
- **Input Container**: Organized layout for text and voice input

### Visual Feedback
- **Recording State**: Button pulses and changes color
- **Status Messages**: Clear feedback during voice processing
- **Error Handling**: Visual indicators for issues

## 🧪 Testing Voice Input

### Test Script
Run the included test script to verify functionality:

```bash
python test_voice_input.py
```

### Manual Testing
1. Start the bot: `python main.py`
2. Open browser: `http://localhost:8000`
3. Click microphone button
4. Speak a message
5. Verify voice response

## 🔍 Troubleshooting

### Common Issues

#### "Speech recognition not supported"
- **Solution**: Use Chrome or Edge browser
- **Alternative**: Text input still works

#### "Microphone access denied"
- **Solution**: Allow microphone access in browser
- **Check**: Browser permissions for the site

#### "No voice output"
- **Solution**: Voice is automatically enabled for voice input
- **Check**: Audio settings and volume

#### "Poor transcription quality"
- **Solution**: Speak clearly and reduce background noise
- **Check**: Microphone quality and positioning

### Debug Information
- Check browser console for detailed logs
- Voice status shows current state
- Status bar displays connection and processing info

## 📱 Mobile Support

### Mobile Browsers
- **iOS Safari**: Limited support
- **Android Chrome**: Full support ✅
- **Mobile Firefox**: Limited support

### Mobile Considerations
- **Touch-friendly** microphone button
- **Responsive design** for small screens
- **Mobile-optimized** voice recognition

## 🔒 Privacy & Security

### Local Processing
- **Voice recognition** happens in your browser
- **No voice data** sent to external services
- **Text only** sent to AI service (Gemini)

### Data Handling
- **Voice input** is processed locally
- **Transcription** happens in real-time
- **No voice recordings** stored

## 🚀 Future Enhancements

### Planned Features
- **Multiple language support**
- **Voice command shortcuts**
- **Custom wake words**
- **Voice activity detection**
- **Noise cancellation**

### Customization Options
- **Voice recognition sensitivity**
- **Custom voice commands**
- **Voice input languages**
- **Audio quality settings**

## 📚 API Reference

### Voice Message Format
```json
{
  "type": "voice_message",
  "message": "transcribed text",
  "client_agent": "browser info"
}
```

### Voice Response Format
```json
{
  "type": "voice_message_response",
  "message": "AI response text",
  "timestamp": "ISO timestamp",
  "response_time_ms": 1234.56
}
```

## 🎉 Getting Started

1. **Install dependencies**: `pip install -r requirements.txt`
2. **Configure API key**: Set `GEMINI_API_KEY` in `.env`
3. **Start the bot**: `python main.py`
4. **Open browser**: Navigate to `http://localhost:8000`
5. **Click microphone**: Start using voice input!

## 🤝 Support

### Need Help?
- Check the troubleshooting section above
- Review browser console for errors
- Test with the included test script
- Ensure microphone permissions are granted

### Browser Requirements
- **Modern browser** with Web Speech API support
- **Microphone access** enabled
- **Stable internet connection** for AI responses

---

**🎤 Happy Voice Chatting!** 🎤

Your AI Voice Bot now supports full voice interaction - speak naturally and get voice responses automatically!
