import asyncio
import json
import logging
import uuid
import base64
import time
from datetime import datetime
from typing import Set, Dict
from aiohttp import web
from websockets.server import WebSocketServerProtocol, serve
import os
from pathlib import Path
import argparse
import sys

from server import Config, ChatLogger, GeminiClient, GeminiVoiceService

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ChatbotWebSocketServer:
    def __init__(self):
        self.clients: Set[WebSocketServerProtocol] = set()
        self.conversation_history: Dict[str, list] = {}
        self.ai_client = GeminiClient()
        self.voice_service = GeminiVoiceService()
        self.chat_logger = ChatLogger()

    async def initialize(self):
        await self.ai_client.initialize()
        logger.info("WebSocket server initialized successfully")
    
    async def register_client(self, websocket: WebSocketServerProtocol):
        self.clients.add(websocket)
        client_id = str(uuid.uuid4())
        self.conversation_history[client_id] = []
        welcome_message = {
            "type": "system",
            "message": "Welcome to AI Voice Bot! I'm powered by Google's Gemini AI. How can I help you today?",
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
            if message_type == 'message':
                await self.handle_chat_message(websocket, data, client_id)
            elif message_type == 'voice_request':
                await self.handle_voice_request(websocket, data, client_id)
            else:
                logger.warning(f"Unknown message type: {message_type}")
        except json.JSONDecodeError:
            error_message = {"type": "error", "message": "Invalid JSON format", "timestamp": datetime.now().isoformat()}
            await websocket.send(json.dumps(error_message))
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error_message = {"type": "error", "message": "An error occurred while processing your message", "timestamp": datetime.now().isoformat()}
            await websocket.send(json.dumps(error_message))
    
    async def handle_chat_message(self, websocket: WebSocketServerProtocol, data: dict, client_id: str):
        user_message = data.get('message', '').strip()
        if not user_message:
            return
        start_time = time.time()
        conversation_history = self.conversation_history.get(client_id, [])
        ai_response = await self.ai_client.generate_response(user_message, conversation_history)
        response_time = (time.time() - start_time) * 1000
        conversation_entry = {'user': user_message, 'assistant': ai_response, 'timestamp': datetime.now().isoformat()}
        conversation_history.append(conversation_entry)
        self.conversation_history[client_id] = conversation_history
        response_message = {"type": "assistant", "message": ai_response, "timestamp": datetime.now().isoformat(), "response_time_ms": round(response_time, 2)}
        await websocket.send(json.dumps(response_message))
        await self.chat_logger.log_chat({
            'timestamp': datetime.now().isoformat(), 'session_id': client_id, 'message_type': 'chat',
            'user_message': user_message, 'assistant_response': ai_response, 'response_time_ms': round(response_time, 2),
            'user_ip': websocket.remote_address[0] if websocket.remote_address else 'unknown', 'message_length': len(user_message),
            'voice_generated': False, 'voice_voice_name': '', 'error_message': '',
            'client_agent': data.get('client_agent', 'unknown'), 'processing_status': 'success'
        })
        logger.info(f"Processed message from client {client_id[:8]}... in {response_time:.2f}ms")
    
    async def handle_voice_request(self, websocket: WebSocketServerProtocol, data: dict, client_id: str):
        try:
            text = data.get('text', '').strip()
            voice_name = data.get('voice', 'Kore')
            if not text:
                await websocket.send(json.dumps({"type": "error", "message": "No text provided for voice generation", "timestamp": datetime.now().isoformat()}))
                return
            audio_data = await self.voice_service.generate_speech(text, voice_name)
            if audio_data:
                audio_base64 = base64.b64encode(audio_data).decode('utf-8')
                await websocket.send(json.dumps({"type": "voice_response", "audio_data": audio_base64, "text": text, "voice": voice_name, "timestamp": datetime.now().isoformat()}))
                logger.info(f"Generated voice for client {client_id[:8]}... text: {text[:50]}...")
                await self.chat_logger.log_chat({
                    'timestamp': datetime.now().isoformat(), 'session_id': client_id, 'message_type': 'voice_request',
                    'user_message': '', 'assistant_response': text, 'response_time_ms': 0,
                    'user_ip': websocket.remote_address[0] if websocket.remote_address else 'unknown', 'message_length': len(text),
                    'voice_generated': True, 'voice_voice_name': voice_name, 'error_message': '',
                    'client_agent': data.get('client_agent', 'unknown'), 'processing_status': 'success'
                })
            else:
                await websocket.send(json.dumps({"type": "error", "message": "Failed to generate voice", "timestamp": datetime.now().isoformat()}))
                await self.chat_logger.log_chat({
                    'timestamp': datetime.now().isoformat(), 'session_id': client_id, 'message_type': 'voice_request',
                    'user_message': '', 'assistant_response': text, 'response_time_ms': 0,
                    'user_ip': websocket.remote_address[0] if websocket.remote_address else 'unknown', 'message_length': len(text),
                    'voice_generated': False, 'voice_voice_name': voice_name, 'error_message': 'Failed to generate voice',
                    'client_agent': data.get('client_agent', 'unknown'), 'processing_status': 'error'
                })
        except Exception as e:
            logger.error(f"Error handling voice request: {e}")
            await websocket.send(json.dumps({"type": "error", "message": "An error occurred while generating voice", "timestamp": datetime.now().isoformat()}))
            await self.chat_logger.log_chat({
                'timestamp': datetime.now().isoformat(), 'session_id': client_id, 'message_type': 'voice_request',
                'user_message': '', 'assistant_response': text, 'response_time_ms': 0,
                'user_ip': websocket.remote_address[0] if websocket.remote_address else 'unknown', 'message_length': len(text),
                'voice_generated': False, 'voice_voice_name': voice_name, 'error_message': str(e),
                'client_agent': data.get('client_agent', 'unknown'), 'processing_status': 'error'
            })
    
    async def handle_client(self, websocket: WebSocketServerProtocol):
        client_id = None
        try:
            client_id = await self.register_client(websocket)
            async for message in websocket:
                await self.handle_message(websocket, message, client_id)
        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed normally")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            if client_id:
                await self.unregister_client(websocket, client_id)

    async def start_server(self):
        await self.initialize()
        server = await serve(self.handle_client, Config.WS_HOST, Config.WS_PORT)
        logger.info(f"WebSocket server started on ws://{Config.WS_HOST}:{Config.WS_PORT}")
        logger.info(f"Gemini client ready: {self.ai_client.is_ready()}")
        await server.wait_closed()

class CombinedServer:
    def __init__(self):
        self.websocket_server = ChatbotWebSocketServer()
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        static_path = Path(__file__).parent / 'static'
        self.app.router.add_static('/static', static_path)
        self.app.router.add_get('/', self.serve_index)
        self.app.router.add_get('/index.html', self.serve_index)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/logs', self.serve_logs)
        self.app.router.add_get('/logs/recent', self.get_recent_logs)
        self.app.router.add_get('/logs/summary', self.get_log_summary)
        self.app.router.add_post('/logs/clear', self.clear_logs)
        self.app.router.add_get('/logs/export', self.export_logs_csv)
    
    async def serve_index(self, request):
        index_path = Path(__file__).parent / 'static' / 'index.html'
        if index_path.exists():
            return web.FileResponse(index_path)
        else:
            return web.Response(text="Index file not found", status=404)
    
    async def health_check(self, request):
        return web.json_response({
            "status": "healthy",
            "service": "AI Voice Bot",
            "websocket_ready": self.websocket_server.ai_client.is_ready()
        })
    
    async def serve_logs(self, request):
        logs_html = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Voice Bot - Logs</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
                .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 20px; border-bottom: 2px solid #e0e0e0; }
                .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
                .stat-card { background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff; }
                .stat-number { font-size: 2em; font-weight: bold; color: #007bff; }
                .stat-label { color: #666; margin-top: 5px; }
                .controls { margin-bottom: 20px; }
                .btn { background: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; margin-right: 10px; }
                .btn:hover { background: #0056b3; }
                .btn.success { background: #28a745; }
                .btn.warning { background: #ffc107; color: #212529; }
                .btn.danger { background: #dc3545; }
                .logs-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                .logs-table th, .logs-table td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
                .logs-table th { background: #f8f9fa; font-weight: bold; }
                .logs-table tr:hover { background: #f5f5f5; }
                .message-type { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
                .message-type.chat { background: #d4edda; color: #155724; }
                .message-type.voice_request { background: #d1ecf1; color: #0c5460; }
                .status-success { background: #d4edda; color: #155724; }
                .status-error { background: #f8d7da; color: #721c24; }
                .refresh-info { color: #666; font-style: italic; margin-top: 10px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🤖 AI Voice Bot - Activity Logs</h1>
                    <div>
                        <a href="/" class="btn">← Back to Chat</a>
                        <button class="btn success" onclick="refreshLogs()">🔄 Refresh</button>
                    </div>
                </div>
                
                <div class="stats" id="stats">
                    <div class="stat-card">
                        <div class="stat-number" id="totalMessages">-</div>
                        <div class="stat-label">Total Messages</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="uniqueSessions">-</div>
                        <div class="stat-label">Unique Sessions</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="avgResponseTime">-</div>
                        <div class="stat-label">Avg Response Time (ms)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="voiceRequests">-</div>
                        <div class="stat-label">Voice Requests</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="successRate">-</div>
                        <div class="stat-label">Success Rate (%)</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number" id="errors">-</div>
                        <div class="stat-label">Errors</div>
                    </div>
                </div>
                
                <div class="controls">
                    <button class="btn" onclick="exportCSV()">📊 Export CSV</button>
                    <button class="btn warning" onclick="clearLogs()">🗑️ Clear Logs</button>
                    <span class="refresh-info">Auto-refresh every 30 seconds</span>
                </div>
                
                <table class="logs-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Type</th>
                            <th>Session ID</th>
                            <th>User Message</th>
                            <th>AI Response</th>
                            <th>Response Time</th>
                            <th>Voice</th>
                            <th>Status</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody id="logsTableBody">
                        <tr><td colspan="9">Loading logs...</td></tr>
                    </tbody>
                </table>
            </div>
            
            <script>
                let refreshInterval;
                
                async function loadStats() {
                    try {
                        const response = await fetch('/logs/summary');
                        const stats = await response.json();
                        
                        document.getElementById('totalMessages').textContent = stats.total_messages || 0;
                        document.getElementById('uniqueSessions').textContent = stats.unique_sessions || 0;
                        document.getElementById('avgResponseTime').textContent = stats.average_response_time_ms || 0;
                        document.getElementById('voiceRequests').textContent = stats.voice_requests || 0;
                        document.getElementById('successRate').textContent = stats.success_rate || 0;
                        document.getElementById('errors').textContent = stats.errors || 0;
                    } catch (error) {
                        console.error('Error loading stats:', error);
                    }
                }
                
                async function loadLogs() {
                    try {
                        const response = await fetch('/logs/recent');
                        const logs = await response.json();
                        
                        const tbody = document.getElementById('logsTableBody');
                        tbody.innerHTML = '';
                        
                        if (logs.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="9">No logs found</td></tr>';
                            return;
                        }
                        
                        logs.forEach(log => {
                            const row = document.createElement('tr');
                            
                            const timestamp = new Date(log.timestamp).toLocaleString();
                            const messageType = log.message_type || 'unknown';
                            const status = log.processing_status || 'unknown';
                            
                            row.innerHTML = `
                                <td>${timestamp}</td>
                                <td><span class="message-type ${messageType}">${messageType}</span></td>
                                <td>${log.session_id?.substring(0, 8) || 'N/A'}...</td>
                                <td>${log.user_message || 'N/A'}</td>
                                <td>${log.assistant_response || 'N/A'}</td>
                                <td>${log.response_time_ms || 'N/A'}ms</td>
                                <td>${log.voice_generated === 'True' ? '✅ ' + (log.voice_voice_name || 'Kore') : '❌'}</td>
                                <td><span class="status-${status}">${status}</span></td>
                                <td>${log.user_ip || 'N/A'}</td>
                            `;
                            
                            tbody.appendChild(row);
                        });
                    } catch (error) {
                        console.error('Error loading logs:', error);
                        document.getElementById('logsTableBody').innerHTML = '<tr><td colspan="9">Error loading logs</td></tr>';
                    }
                }
                
                function refreshLogs() {
                    loadStats();
                    loadLogs();
                }
                
                function exportCSV() {
                    window.open('/logs', '_blank');
                }
                
                async function clearLogs() {
                    if (confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
                        try {
                            const response = await fetch('/logs/clear', { method: 'POST' });
                            if (response.ok) {
                                refreshLogs();
                                alert('Logs cleared successfully!');
                            } else {
                                alert('Failed to clear logs');
                            }
                        } catch (error) {
                            console.error('Error clearing logs:', error);
                            alert('Error clearing logs');
                        }
                    }
                }
                
                function startAutoRefresh() {
                    refreshInterval = setInterval(refreshLogs, 30000);
                }
                
                function stopAutoRefresh() {
                    if (refreshInterval) {
                        clearInterval(refreshInterval);
                    }
                }
                
                document.addEventListener('DOMContentLoaded', () => {
                    loadStats();
                    loadLogs();
                    startAutoRefresh();
                });
                
                window.addEventListener('beforeunload', stopAutoRefresh);
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
            logger.error(f"Error getting recent logs: {e}")
            return web.json_response([], status=500)
    
    async def get_log_summary(self, request):
        try:
            summary = await self.websocket_server.chat_logger.get_log_summary()
            return web.json_response(summary)
        except Exception as e:
            logger.error(f"Error getting log summary: {e}")
            return web.json_response({}, status=500)
    
    async def clear_logs(self, request):
        try:
            log_file = self.websocket_server.chat_logger.get_log_file_path()
            with open(log_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.websocket_server.chat_logger.csv_headers)
                writer.writeheader()
            logger.info("Logs cleared successfully")
            return web.json_response({"status": "success", "message": "Logs cleared successfully"})
        except Exception as e:
            logger.error(f"Error clearing logs: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    
    async def export_logs_csv(self, request):
        try:
            logs = await self.websocket_server.chat_logger.get_recent_logs(10000)
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=self.websocket_server.chat_logger.csv_headers)
            writer.writeheader()
            for log in logs:
                writer.writerow(log)
            csv_content = output.getvalue()
            output.close()
            return web.Response(
                text=csv_content,
                content_type='text/csv',
                headers={'Content-Disposition': 'attachment; filename="ai_voice_bot_logs.csv"'}
            )
        except Exception as e:
            logger.error(f"Error exporting logs: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    
    async def start_servers(self):
        websocket_task = asyncio.create_task(self.websocket_server.start_server())
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8000)
        await site.start()
        logger.info("HTTP server started on http://localhost:8000")
        logger.info("WebSocket server started on ws://localhost:8765")
        try:
            await websocket_task
        except KeyboardInterrupt:
            logger.info("Shutting down servers...")
        finally:
            await runner.cleanup()

async def main():
    parser = argparse.ArgumentParser(description='AI Voice Bot Startup Script')
    parser.add_argument('--port', type=int, default=8765, help='WebSocket port (default: 8765)')
    parser.add_argument('--host', default='localhost', help='WebSocket host (default: localhost)')
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
    
    if not args.demo and not Config.GEMINI_API_KEY:
        print("❌ Gemini API key not configured!")
        print("💡 Please update GEMINI_API_KEY in the .env file.")
        sys.exit(1)

    print("🚀 Starting AI Voice Bot...")
    print("📱 Open your browser and navigate to:")
    print(f"   http://{args.host}:{args.http_port}")
    print("⏹️ Press Ctrl+C to stop the server")
    print("=" * 60)
    
    server = CombinedServer()
    await server.start_servers()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Goodbye!")