# AI Voice Bot with Gemini AI

A real-time AI chatbot with text-to-speech capabilities powered by Google's Gemini AI.

## Features

- 🤖 **AI Chat**: Powered by Google Gemini 2.0 Flash
- 🔊 **Text-to-Speech**: Multiple voice options (Kore, Nova, Fable, Echo)
- 💬 **Real-time Chat**: WebSocket-based communication
- 📱 **Modern UI**: Responsive web interface
- 📊 **Chat Logging**: Comprehensive logging and analytics
- 🎵 **Audio Queue**: Smart audio playback management

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Gemini API Key

Create a `.env` file in the project root with your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

**Get your API key from:** [Google AI Studio](https://makersuite.google.com/app/apikey)

### 3. Run the Application

```bash
python client.py
```

The application will start:
- HTTP Server: http://localhost:8000
- WebSocket Server: ws://localhost:8765

### 4. Open in Browser

Navigate to http://localhost:8000 in your web browser.

## Voice Configuration

### Available Voices
- **Kore** (default): Friendly and approachable
- **Nova**: Professional and clear
- **Fable**: Warm and engaging
- **Echo**: Natural and conversational

### Voice Controls
- Click the voice button to enable/disable text-to-speech
- Select different voices from the dropdown
- AI responses will automatically be spoken when voice is enabled

## Testing Voice Service

Run the voice service test:

```bash
python test_voice.py
```

This will test:
- API key configuration
- Voice generation
- Cache functionality
- Multiple voice options

## Troubleshooting

### Common Issues

1. **Port Already in Use**
   - Stop any existing instances
   - Check for processes using ports 8000 or 8765

2. **Voice Not Working**
   - Verify API key is set correctly
   - Check browser console for errors
   - Ensure audio is not muted

3. **Connection Errors**
   - Check firewall settings
   - Verify WebSocket connection
   - Check browser compatibility

### Logs

Chat logs are saved to `chat_logs.csv` and can be viewed at:
- http://localhost:8000/logs

## API Endpoints

- `GET /` - Main chat interface
- `GET /health` - Health check
- `GET /logs` - View chat logs
- `GET /logs/recent` - Recent chat history
- `GET /logs/summary` - Chat statistics

## WebSocket Messages

### Client to Server
```json
{
  "type": "message",
  "message": "Hello AI!",
  "client_agent": "Mozilla/5.0..."
}
```

```json
{
  "type": "voice_request",
  "text": "Text to speak",
  "voice": "Kore"
}
```

### Server to Client
```json
{
  "type": "assistant",
  "message": "Hello! How can I help you?",
  "timestamp": "2025-08-29T10:00:00",
  "response_time_ms": 150.5
}
```

```json
{
  "type": "voice_response",
  "audio_data": "base64_encoded_audio",
  "text": "Text that was spoken",
  "voice": "Kore"
}
```

## Development

### Project Structure
```
AI_Bot/
├── client.py          # Main application entry point
├── server.py          # AI services and utilities
├── static/            # Web interface files
│   ├── index.html     # Main HTML page
│   ├── script.js      # Frontend JavaScript
│   └── styles.css     # Styling
├── requirements.txt   # Python dependencies
├── test_voice.py      # Voice service test script
└── README.md          # This file
```

### Adding New Features
1. Modify `server.py` for backend logic
2. Update `client.py` for WebSocket handling
3. Enhance `static/` files for UI changes
4. Test with `test_voice.py`

## License

This project is open source and available under the MIT License.

