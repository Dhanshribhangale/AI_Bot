import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your-gemini-api-key-here')
    WS_HOST = os.getenv('WS_HOST', 'localhost')
    WS_PORT = int(os.getenv('WS_PORT', 8765))
    LOG_FILE = os.getenv('LOG_FILE', 'chat_logs.csv')
    CHAT_MODEL = "gemini-2.0-flash-exp"
    TTS_MODEL = "gemini-2.5-flash-preview-tts"
    MAX_TOKENS = 1000
    TEMPERATURE = 0.7