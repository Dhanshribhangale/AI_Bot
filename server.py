import asyncio
import aiofiles
import csv
import os
from datetime import datetime
from typing import Dict, Any, Optional
import google.generativeai as genai
from google.genai import types
import logging
import time
import io
import struct
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

class ChatLogger:
    def __init__(self, log_file: str = None):
        self.log_file = log_file or Config.LOG_FILE
        self.csv_headers = [
            'timestamp', 'session_id', 'message_type', 'user_message', 'assistant_response',
            'response_time_ms', 'user_ip', 'message_length', 'voice_generated', 'voice_voice_name',
            'error_message', 'client_agent', 'processing_status'
        ]
        self._ensure_log_file_exists()

    def _ensure_log_file_exists(self):
        if not os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                    writer.writeheader()
            except Exception as e:
                logger.error(f"Error creating log file: {e}")

    async def log_chat(self, chat_data: Dict[str, Any]):
        try:
            log_entry = {
                header: chat_data.get(header, '') for header in self.csv_headers
            }
            log_entry['timestamp'] = log_entry['timestamp'] or datetime.now().isoformat()
            log_entry['session_id'] = log_entry['session_id'] or 'unknown'
            log_entry['message_type'] = log_entry['message_type'] or 'chat'
            
            async with aiofiles.open(self.log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.csv_headers)
                await f.write(','.join([f'"{str(log_entry.get(h, "")).replace("\"", "\"\"")}"' for h in self.csv_headers]) + '\n')

        except Exception as e:
            logger.error(f"Error logging chat: {e}")
            
    async def get_chat_statistics(self) -> Dict[str, Any]:
        try:
            total_messages, total_response_time, unique_sessions = 0, 0, set()
            async with aiofiles.open(self.log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                lines = content.strip().split('\n')[1:]
                for line in lines:
                    if line.strip():
                        try:
                            row = next(csv.DictReader([line], fieldnames=self.csv_headers))
                            total_messages += 1
                            total_response_time += float(row.get('response_time_ms', 0))
                            unique_sessions.add(row.get('session_id', ''))
                        except Exception:
                            continue
            avg_response_time = total_response_time / total_messages if total_messages > 0 else 0
            return {
                'total_messages': total_messages,
                'unique_sessions': len(unique_sessions),
                'average_response_time_ms': round(avg_response_time, 2)
            }
        except Exception as e:
            logger.error(f"Error getting chat statistics: {e}")
            return {}
            
    def get_log_file_path(self) -> str:
        return os.path.abspath(self.log_file)
        
    async def get_recent_logs(self, limit: int = 50) -> list:
        try:
            logs = []
            async with aiofiles.open(self.log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                lines = content.strip().split('\n')
                if len(lines) > 1:
                    data_lines = lines[1:]
                    recent_lines = data_lines[-limit:] if len(data_lines) > limit else data_lines
                    for line in recent_lines:
                        if line.strip():
                            try:
                                row = next(csv.DictReader([line], fieldnames=self.csv_headers))
                                logs.append(row)
                            except Exception:
                                continue
                return logs[::-1]
        except Exception as e:
            logger.error(f"Error getting recent logs: {e}")
            return []
            
    async def get_log_summary(self) -> Dict[str, Any]:
        try:
            total_messages, total_response_time, voice_requests, errors = 0, 0, 0, 0
            unique_sessions = set()
            async with aiofiles.open(self.log_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                lines = content.strip().split('\n')[1:]
                for line in lines:
                    if line.strip():
                        try:
                            row = next(csv.DictReader([line], fieldnames=self.csv_headers))
                            total_messages += 1
                            total_response_time += float(row.get('response_time_ms', 0))
                            unique_sessions.add(row.get('session_id', ''))
                            if row.get('voice_generated') == 'True':
                                voice_requests += 1
                            if row.get('processing_status') == 'error':
                                errors += 1
                        except Exception:
                            continue
            avg_response_time = total_response_time / total_messages if total_messages > 0 else 0
            success_rate = ((total_messages - errors) / total_messages * 100) if total_messages > 0 else 0
            return {
                'total_messages': total_messages,
                'unique_sessions': len(unique_sessions),
                'average_response_time_ms': round(avg_response_time, 2),
                'voice_requests': voice_requests,
                'errors': errors,
                'success_rate': round(success_rate, 2)
            }
        except Exception as e:
            logger.error(f"Error getting log summary: {e}")
            return {}

class GeminiClient:
    def __init__(self):
        self.client = None
        self.initialized = False

    async def initialize(self):
        try:
            api_key = Config.GEMINI_API_KEY
            if not api_key:
                logger.error("Gemini API key not configured")
                return False
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(Config.CHAT_MODEL)
            self.initialized = True
            logger.info("Gemini client initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            self.initialized = False
            return False

    async def generate_response(self, user_message: str, conversation_history: list = None) -> Optional[str]:
        if not self.initialized:
            success = await self.initialize()
            if not success:
                return "Sorry, I'm having trouble connecting to the AI service. Please check your configuration."
        try:
            context = ""
            if conversation_history:
                context_parts = []
                for msg in conversation_history[-5:]:
                    context_parts.append(f"User: {msg['user']}")
                    context_parts.append(f"Assistant: {msg['assistant']}")
                context = "\n".join(context_parts) + "\n\n"
            full_prompt = f"""You are a helpful AI assistant. Be concise, friendly, and helpful in your responses.\n\n{context}User: {user_message}\nAssistant:"""
            response = await asyncio.to_thread(
                self.model.generate_content,
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=Config.MAX_TOKENS,
                    temperature=Config.TEMPERATURE
                )
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error while processing your request. Please try again."

    def is_ready(self) -> bool:
        return self.initialized

class GeminiVoiceService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.TTS_MODEL
        # genai.Client is no longer needed. configure() handles everything globally.
        self.audio_cache: Dict[str, bytes] = {}
        self.cache_size_limit = 50

    async def generate_speech(self, text: str, voice_name: str = "Kore") -> Optional[bytes]:
        try:
            cache_key = f"{text}_{voice_name}"
            if cache_key in self.audio_cache:
                logger.info(f"Audio cache hit for: {text[:30]}...")
                return self.audio_cache[cache_key]
            
            start_time = time.time()
            logger.info(f"Generating speech for: {text[:30]}...")
            
            # Use the global genai client initialized by GeminiClient
            response = await asyncio.to_thread(
                genai.GenerativeModel(self.model).generate_content,
                contents=f"Say cheerfully: {text}",
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
            
            if (response.candidates and 
                response.candidates[0].content and
                response.candidates[0].content.parts and
                response.candidates[0].content.parts[0].inline_data):
                
                audio_data = response.candidates[0].content.parts[0].inline_data.data
                
                if audio_data:
                    wav_data = self.convert_pcm_to_wav(audio_data)
                    self._add_to_cache(cache_key, wav_data)
                    generation_time = time.time() - start_time
                    logger.info(f"Speech generated in {generation_time:.2f}s for: {text[:30]}...")
                    return wav_data
                else:
                    logger.error("No audio data in response")
                    return None
            else:
                logger.error("Invalid response format from Gemini TTS API")
                return None
                        
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            return None
    
    def _add_to_cache(self, key: str, audio_data: bytes):
        try:
            if len(self.audio_cache) >= self.cache_size_limit:
                oldest_key = next(iter(self.audio_cache))
                del self.audio_cache[oldest_key]
                logger.debug(f"Removed oldest cache entry: {oldest_key}")
            self.audio_cache[key] = audio_data
            logger.debug(f"Added to cache: {key}")
        except Exception as e:
            logger.warning(f"Cache operation failed: {e}")
    
    def clear_cache(self):
        self.audio_cache.clear()
        logger.info("Audio cache cleared")
    
    def get_cache_stats(self) -> Dict[str, int]:
        return {
            'cache_size': len(self.audio_cache),
            'cache_limit': self.cache_size_limit
        }
    
    def convert_pcm_to_wav(self, pcm_data: bytes) -> bytes:
        try:
            wav_buffer = io.BytesIO()
            channels, sample_width, sample_rate = 1, 2, 24000
            frame_rate = sample_rate * channels * sample_width
            data_size = len(pcm_data)
            file_size = 36 + data_size
            
            wav_buffer.write(b'RIFF')
            wav_buffer.write(struct.pack('<I', file_size))
            wav_buffer.write(b'WAVE')
            wav_buffer.write(b'fmt ')
            wav_buffer.write(struct.pack('<I', 16))
            wav_buffer.write(struct.pack('<H', 1))
            wav_buffer.write(struct.pack('<H', channels))
            wav_buffer.write(struct.pack('<I', sample_rate))
            wav_buffer.write(struct.pack('<I', frame_rate))
            wav_buffer.write(struct.pack('<H', channels * sample_width))
            wav_buffer.write(struct.pack('<H', sample_width * 8))
            wav_buffer.write(b'data')
            wav_buffer.write(struct.pack('<I', data_size))
            wav_buffer.write(pcm_data)
            
            wav_data = wav_buffer.getvalue()
            wav_buffer.close()
            
            logger.info(f"Converted PCM to WAV: {len(pcm_data)} -> {len(wav_data)} bytes")
            return wav_data
        except Exception as e:
            logger.error(f"Error converting PCM to WAV: {e}")
            return pcm_data