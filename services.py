import asyncio
import aiofiles
import csv
import os
from datetime import datetime
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
import logging
import time
import io
import struct
import subprocess

# Add google-cloud-speech for real STT
# You will need to install it: pip install google-cloud-speech
from google.cloud import speech

from config import Config
from collections import deque

logger = logging.getLogger(__name__)

# --- NEW: Real Speech-to-Text Service using Google Cloud STT ---
# This replaces the DummySTTService
class GoogleSTTService:
    def __init__(self):
        # This will automatically use the credentials set up in your environment
        # (e.g., GOOGLE_APPLICATION_CREDENTIALS environment variable)
        try:
            self.client = speech.SpeechAsyncClient()
            logger.info("Google Cloud Speech-to-Text client initialized.")
        except Exception as e:
            self.client = None
            logger.error(f"Could not initialize Google STT client: {e}")
            logger.error("Please ensure you have authenticated with Google Cloud SDK.")

    async def transcribe_audio(self, audio_data: bytes, confidence_threshold: float = 0.7):
        if not self.client:
            return {
                "raw_text": "",
                "cleaned_text": "",
                "confidence": 0.0,
                "error": "STT service is not configured."
            }
            
        recognition_audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000, # Matching the TTS output rate
            language_code="en-US",
            enable_automatic_punctuation=True
        )

        try:
            operation = await self.client.long_running_recognize(config=config, audio=recognition_audio)
            response = await asyncio.wrap_future(operation.result(timeout=90))
            
            if response.results:
                best_alternative = response.results[0].alternatives[0]
                text = best_alternative.transcript
                confidence = best_alternative.confidence
                
                # Simple filler word removal
                filler_words = ["um", "uh", "hmm"]
                cleaned_text = ' '.join([word for word in text.split() if word.lower() not in filler_words]).strip()
                
                return {
                    "raw_text": text,
                    "cleaned_text": cleaned_text,
                    "confidence": confidence
                }
            else:
                return {"raw_text": "", "cleaned_text": "", "confidence": 0.0}
        except Exception as e:
            logger.error(f"Error during STT transcription: {e}")
            return {"raw_text": "", "cleaned_text": "", "confidence": 0.0, "error": str(e)}

# --- NEW: Utility for Server-Side Audio Playback ---
class AudioPlaybackService:
    @staticmethod
    def play_audio_server_side(audio_data: bytes):
        """Plays audio data on the server using ffplay."""
        try:
            # ffplay is part of the ffmpeg suite. It needs to be installed on the server.
            command = ["ffplay", "-nodisp", "-autoexit", "-"]
            proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc.communicate(input=audio_data)
            logger.info("Successfully played audio on server.")
            return True
        except FileNotFoundError:
            logger.error("ffplay not found. Please install ffmpeg to use server-side audio playback.")
            return False
        except Exception as e:
            logger.error(f"Error playing audio on server: {e}")
            return False

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
            # For the new google-genai library, we need to set the API key differently
            import os
            os.environ['GOOGLE_API_KEY'] = api_key
            self.model = Config.CHAT_MODEL
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
            
            client = genai.Client()
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=full_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=Config.MAX_TOKENS,
                    temperature=Config.TEMPERATURE
                )
            )
            return response.candidates[0].content.parts[0].text.strip()
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error while processing your request. Please try again."

    def is_ready(self) -> bool:
        return self.initialized
    
    async def smart_summarize(self, text: str):
        try:
            client = genai.Client()
            
            # Summarization
            summary_prompt = f"Summarize the following content concisely:\n\n{text}"
            summary_response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=summary_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=Config.MAX_TOKENS,
                    temperature=Config.TEMPERATURE
                )
            )
            summary = summary_response.candidates[0].content.parts[0].text.strip()

            # Sentiment Detection
            sentiment_prompt = f"Analyze the sentiment of the following text: '{text}'. Respond with a single word: positive, negative, or neutral."
            sentiment_response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=sentiment_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=Config.MAX_TOKENS,
                    temperature=Config.TEMPERATURE
                )
            )
            sentiment = sentiment_response.candidates[0].content.parts[0].text.strip()

            # Key Fact Extraction
            facts_prompt = f"Extract exactly 5 key facts from the following text:\n\n{text}"
            facts_response = await asyncio.to_thread(
                client.models.generate_content,
                model=self.model,
                contents=facts_prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=Config.MAX_TOKENS,
                    temperature=Config.TEMPERATURE
                )
            )
            facts = facts_response.candidates[0].content.parts[0].text.strip()

            # Conditional Resummarization
            if len(summary.split()) > 300:
                resummarize_prompt = f"Resummarize the following text to under 200 words using bullet points:\n\n{summary}"
                resummarized_response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.model,
                    contents=resummarize_prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=Config.MAX_TOKENS,
                        temperature=Config.TEMPERATURE
                    )
                )
                summary = resummarized_response.candidates[0].content.parts[0].text.strip()

            return {
                "summary": summary,
                "sentiment": sentiment,
                "key_facts": facts
            }

        except Exception as e:
            logger.error(f"Error in smart summarizer: {e}")
            return None

class GeminiVoiceService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model = Config.TTS_MODEL
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

            try:
                client = genai.Client()
                
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.model,
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
                
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, 'content') and candidate.content:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                audio_data = part.inline_data.data
                                if audio_data:
                                    if isinstance(audio_data, str):
                                        import base64
                                        audio_data = base64.b64decode(audio_data)
                                    
                                    wav_data = self.convert_pcm_to_wav(audio_data)
                                    self._add_to_cache(cache_key, wav_data)
                                    generation_time = time.time() - start_time
                                    logger.info(f"Speech generated in {generation_time:.2f}s for: {text[:30]}...")
                                    return wav_data
                
                logger.error("No audio data found in response")
                return None
                
            except Exception as api_error:
                logger.error(f"API call failed: {api_error}")
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

class ChatLogger:
    def __init__(self, log_file: str = None):
        self.log_file = log_file or Config.LOG_FILE
        # --- MODIFIED: Added audio_filename to headers ---
        self.csv_headers = [
            'timestamp', 'session_id', 'message_type', 'user_message', 'assistant_response',
            'response_time_ms', 'user_ip', 'message_length', 'voice_generated', 'voice_voice_name',
            'error_message', 'client_agent', 'processing_status', 'audio_filename'
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
                                reader = csv.reader(io.StringIO(line))
                                row_values = next(reader)
                                # Pad row_values if new columns were added to an old log file
                                if len(row_values) < len(self.csv_headers):
                                    row_values.extend([''] * (len(self.csv_headers) - len(row_values)))
                                row = dict(zip(self.csv_headers, row_values))
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
                            reader = csv.reader(io.StringIO(line))
                            row_values = next(reader)
                            if len(row_values) < len(self.csv_headers):
                                    row_values.extend([''] * (len(self.csv_headers) - len(row_values)))
                            row = dict(zip(self.csv_headers, row_values))
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

class JsonFlattener:
    def flatten_dfs(self, data: dict, parent_key: str = '', sep: str = '.') -> dict:
        items = {}
        for k, v in data.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.update(self.flatten_dfs(v, new_key, sep=sep))
            else:
                items[new_key] = v
        return items

    def flatten_bfs(self, data: dict, sep: str = '.') -> dict:
        from collections import deque
        queue = deque([(data, '')])
        flattened = {}
        while queue:
            current_dict, parent_key = queue.popleft()
            for key, value in current_dict.items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                if isinstance(value, dict):
                    queue.append((value, new_key))
                else:
                    flattened[new_key] = value
        return flattened