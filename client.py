import asyncio
import json
import logging
import uuid
import base64
import time
import csv
import io
from datetime import datetime
from typing import Set, Dict
from aiohttp import web
from websockets.server import WebSocketServerProtocol, serve
import os
from pathlib import Path
import argparse
import sys

from services import Config, ChatLogger, GeminiClient, GeminiVoiceService, JsonFlattener, GoogleSTTService, AudioPlaybackService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatbotWebSocketServer:
    def __init__(self):
        self.clients: Set[WebSocketServerProtocol] = set()
        self.conversation_history: Dict[str, list] = {}
        self.ai_client = GeminiClient()
        self.voice_service = GeminiVoiceService()
        self.chat_logger = ChatLogger()
        self.json_flattener = JsonFlattener()
        self.stt_service = GoogleSTTService()
        self.playback_service = AudioPlaybackService()

    async def initialize(self):
        await self.ai_client.initialize()
        logger.info("WebSocket server initialized successfully")

    async def register_client(self, websocket: WebSocketServerProtocol):
        self.clients.add(websocket)
        client_id = str(uuid.uuid4())
        self.conversation_history[client_id] = []
        welcome_message = {
            "type": "system",
            "message": "Welcome to AI Voice Bot! I'm powered by Google's Gemini AI. How can I help you today?\n\nYou can also use commands:\n- `/summarize <text to summarize>`\n- `/flatten <JSON object>`\n- `/play <text to speak on server>`",
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id
        }
        await websocket.send(json.dumps(welcome_message))
        logger.info(f"New client connected. Total clients: {len(self.clients)}")
        return client_id

    async def unregister_client(self, websocket: WebSocketServerProtocol, client_id: str):
        self.clients.discard(websocket)
        if client_id in self.conversation_history:
            del self.conversation_history[client_id]
        logger.info(f"Client disconnected. Total clients: {len(self.clients)}")

    async def handle_message(self, websocket: WebSocketServerProtocol, message: str, client_id: str):
        try:
            data = json.loads(message)
            message_type = data.get('type', 'message')

            if message_type == 'message' or message_type == 'voice_message':
                await self.handle_chat_message(websocket, data, client_id)
            elif message_type == 'voice_request':
                await self.handle_voice_request(websocket, data, client_id)
            elif message_type == 'audio_upload':
                await self.handle_audio_upload(websocket, data, client_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except json.JSONDecodeError:
            error_message = {"type": "error", "message": "Invalid JSON format"}
            await websocket.send(json.dumps(error_message))
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_message = {"type": "error", "message": "An error occurred while processing your message"}
            await websocket.send(json.dumps(error_message))

    async def handle_chat_message(self, websocket: WebSocketServerProtocol, data: dict, client_id: str):
        user_message = data.get('message', '').strip()
        if not user_message:
            return

        start_time = time.time()
        
        if user_message.lower().startswith('/summarize '):
            text_to_summarize = user_message[11:].strip()
            if not text_to_summarize:
                response = {"type": "assistant", "message": "Please provide text to summarize. Usage: /summarize <text>"}
                await websocket.send(json.dumps(response))
                return
            
            thinking_msg = {"type": "system", "message": "Analyzing your text..."}
            await websocket.send(json.dumps(thinking_msg))
            summary_result = await self.ai_client.smart_summarize(text_to_summarize)

            if summary_result:
                response_text = (
                    f"**📝 Smart Summary Report**\n\n"
                    f"**Sentiment:** {summary_result['sentiment']}\n\n"
                    f"**Key Facts:**\n{summary_result['key_facts']}\n\n"
                    f"**Summary:**\n{summary_result['summary']}"
                )
            else:
                response_text = "Sorry, I couldn't generate a summary. Please try again."
            response_message = {"type": "assistant", "message": response_text}
            await websocket.send(json.dumps(response_message))

        elif user_message.lower().startswith('/flatten '):
            json_string = user_message[9:].strip()
            try:
                json_data = json.loads(json_string)
                if not isinstance(json_data, dict):
                    raise TypeError("Input must be a JSON object.")
                
                dfs_result = self.json_flattener.flatten_dfs(json_data)
                bfs_result = self.json_flattener.flatten_bfs(json_data)

                response_text = (
                    f"**📊 JSON Flattening Results**\n\n"
                    f"**DFS Result:**\n```json\n{json.dumps(dfs_result, indent=2)}\n```\n\n"
                    f"**BFS Result:**\n```json\n{json.dumps(bfs_result, indent=2)}\n```"
                )
            except Exception as e:
                response_text = f"Error: {e}"
            response_message = {"type": "assistant", "message": response_text}
            await websocket.send(json.dumps(response_message))

        elif user_message.lower().startswith('/play '):
            text_to_play = user_message[6:].strip()
            if not text_to_play:
                await websocket.send(json.dumps({"type": "error", "message": "Please provide text. Usage: /play <text>"}))
                return
            
            await websocket.send(json.dumps({"type": "system", "message": f"Generating audio for server playback..."}))
            audio_data = await self.voice_service.generate_speech(text_to_play)
            if audio_data:
                played = self.playback_service.play_audio_server_side(audio_data)
                if played:
                    final_msg = {"type": "system", "message": "Audio played on server."}
                else:
                    final_msg = {"type": "error", "message": "Failed to play audio. Is ffmpeg installed?"}
            else:
                final_msg = {"type": "error", "message": "Could not generate audio."}
            await websocket.send(json.dumps(final_msg))
        
        else:
            conversation_history = self.conversation_history.get(client_id, [])
            ai_response = await self.ai_client.generate_response(user_message, conversation_history)
            response_time = (time.time() - start_time) * 1000
            
            conversation_entry = {'user': user_message, 'assistant': ai_response}
            conversation_history.append(conversation_entry)
            
            response_type = 'voice_message_response' if data.get('type') == 'voice_message' else 'assistant'
            
            response_message = {
                "type": response_type,
                "message": ai_response,
                "response_time_ms": round(response_time, 2)
            }
            await websocket.send(json.dumps(response_message))

    async def handle_audio_upload(self, websocket: WebSocketServerProtocol, data: dict, client_id: str):
        try:
            audio_b64 = data.get('audio_data')
            if not audio_b64:
                await websocket.send(json.dumps({"type": "error", "message": "No audio data received."}))
                return

            await websocket.send(json.dumps({"type": "system", "message": "Transcribing audio..."}))
            audio_data = base64.b64decode(audio_b64)
            stt_result = await self.stt_service.transcribe_audio(audio_data)
            
            transcribed_text = stt_result.get("cleaned_text", "")
            if not transcribed_text or stt_result.get("confidence", 0) < 0.7:
                await websocket.send(json.dumps({"type": "error", "message": "Could not understand the audio clearly."}))
                return

            await websocket.send(json.dumps({"type": "user_transcript", "message": transcribed_text}))
            await self.handle_chat_message(websocket, {"type": "voice_message", "message": transcribed_text}, client_id)
        except Exception as e:
            logger.error(f"Error in handle_audio_upload: {e}")
            await websocket.send(json.dumps({"type": "error", "message": "Server error while processing audio."}))

    async def handle_voice_request(self, websocket: WebSocketServerProtocol, data: dict, client_id: str):
        try:
            text = data.get('text', '').strip()
            voice_name = data.get('voice', 'Kore') # Default to a valid voice
            message_id = data.get('messageId')

            if not text:
                await websocket.send(json.dumps({"type": "error", "message": "No text provided for voice."}))
                return

            audio_data = await self.voice_service.generate_speech(text, voice_name)
            
            if audio_data:
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                response = {
                    "type": "voice_response",
                    "audio_data": audio_base64,
                    "messageId": message_id
                }
                await websocket.send(json.dumps(response))
            else:
                await websocket.send(json.dumps({"type": "error", "message": "Failed to generate voice.", "messageId": message_id}))
        except Exception as e:
            logger.error(f"Error in handle_voice_request: {e}")
            await websocket.send(json.dumps({"type": "error", "message": "Server error during voice generation."}))

    async def handle_client(self, websocket: WebSocketServerProtocol):
        client_id = None
        try:
            client_id = await self.register_client(websocket)
            async for message in websocket:
                await self.handle_message(websocket, message, client_id)
        finally:
            if client_id:
                await self.unregister_client(websocket, client_id)

    async def start_server(self, host=None, port=None):
        await self.initialize()
        host = host or Config.WS_HOST
        port = port or Config.WS_PORT
        async with serve(self.handle_client, host, port) as server:
            logger.info(f"WebSocket server started on ws://{host}:{port}")
            await server.wait_closed()

class CombinedServer:
    def __init__(self):
        self.websocket_server = ChatbotWebSocketServer()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        static_path = Path(__file__).parent / 'static'
        self.app.router.add_static('/static', static_path, show_index=True)
        self.app.router.add_get('/', self.serve_index)
        self.app.router.add_get('/logs', self.serve_logs)
        self.app.router.add_get('/logs/recent', self.get_recent_logs)
        self.app.router.add_get('/logs/summary', self.get_log_summary)

    async def serve_index(self, request):
        return web.FileResponse(Path(__file__).parent / 'static' / 'index.html')

    async def serve_logs(self, request):
        logs_html = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>Chat Logs</title>
            </head>
            <body>
                <h1>Chat Logs</h1>
                <pre id="log-content">Loading...</pre>
                <script>
                    fetch('/logs/recent')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('log-content').textContent = JSON.stringify(data, null, 2);
                        });
                </script>
            </body>
        </html>
        """
        return web.Response(text=logs_html, content_type='text/html')

    async def get_recent_logs(self, request):
        try:
            logs = await self.websocket_server.chat_logger.get_recent_logs(100)
            return web.json_response(logs)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def get_log_summary(self, request):
        try:
            summary = await self.websocket_server.chat_logger.get_log_summary()
            return web.json_response(summary)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
    
    async def start_servers(self, http_port=8000, ws_port=8765, ws_host='localhost'):
        websocket_task = asyncio.create_task(self.websocket_server.start_server(ws_host, ws_port))
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', http_port)
        await site.start()
        
        logger.info(f"HTTP server running on http://localhost:{http_port}")
        await websocket_task

async def main():
    parser = argparse.ArgumentParser(description='AI Voice Bot')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket port')
    parser.add_argument('--http-port', type=int, default=8000, help='HTTP port')
    parser.add_argument('--host', default='localhost', help='Host for servers')
    args = parser.parse_args()

    server = CombinedServer()
    await server.start_servers(http_port=args.http_port, ws_port=args.port, ws_host=args.host)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server is shutting down.")

