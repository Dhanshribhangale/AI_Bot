#!/usr/bin/env python3
import asyncio
import sys
import argparse
import logging
from server import CombinedServer
from config import Config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description='AI Voice Bot Startup Script')
    parser.add_argument('--port', type=int, default=Config.WS_PORT, help='WebSocket port (default: 8765)')
    parser.add_argument('--host', default=Config.WS_HOST, help='WebSocket host (default: localhost)')
    parser.add_argument('--http-port', type=int, default=8000, help='HTTP port (default: 8000)')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode without Gemini API')
    
    args = parser.parse_args()

    print("---")
    print("🤖 AI VOICE BOT 🤖")
    print("---")
    print(f"WebSocket Server: ws://{args.host}:{args.port}")
    print(f"HTTP Server: http://{args.host}:{args.http_port}")
    print(f"Log File: {Config.LOG_FILE}")
    print(f"AI Service: Google Gemini AI")
    
    if not args.demo and (not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY == 'your-gemini-api-key-here'):
        print("❌ Gemini API key not configured!")
        print("💡 Please update GEMINI_API_KEY in the .env file.")
        sys.exit(1)

    print("🚀 Starting AI Voice Bot...")
    print("📱 Open your browser and navigate to:")
    print(f"   http://{args.host}:{args.http_port}")
    print("⏹️ Press Ctrl+C to stop the server")
    print("=" * 60)
    
    server = CombinedServer()
    await server.start_servers(http_port=args.http_port, ws_port=args.port, ws_host=args.host)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")