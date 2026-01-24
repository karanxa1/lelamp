"""
LeLamp Voice Agent - Powered by Deepgram STT + LLM + Edge TTS

Uses Deepgram for STT + LLM, and Edge TTS for ultra-low latency voice output.
Optimized for Raspberry Pi.
"""

import sys
print("=== LeLamp Agent Starting ===", flush=True)
sys.stdout.flush()

import os
import io
import queue
import json
import asyncio
import threading
import time
import numpy as np
import sounddevice as sd
import edge_tts
from dotenv import load_dotenv
from datetime import datetime, timezone

from deepgram import DeepgramClient

load_dotenv()

print("✓ Loaded environment variables", flush=True)

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

print("✓ Imported Firebase modules", flush=True)

if not firebase_admin._apps:
    print("✓ Initializing Firebase...", flush=True)
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
    print("✓ Firebase initialized", flush=True)
db = firestore.client()
print("✓ Firestore client ready", flush=True)


def log_conversation(user_input: str, ai_response: str):
    """Log conversation to Firestore"""
    try:
        db.collection("conversations").add({
            "timestamp": datetime.now(timezone.utc),
            "user_input": user_input,
            "ai_response": ai_response,
            "input_type": "voice",
            "device": "lelamp",
            "source": "deepgram_edge_tts"
        })
        print("✓ Logged")
    except Exception as e:
        print(f"Firestore error: {e}")


def log_event(event_type: str, data: dict):
    """Log event to Firestore"""
    try:
        db.collection("events").add({
            "timestamp": datetime.now(timezone.utc),
            "event_type": event_type,
            "data": data,
            "device": "lelamp"
        })
    except Exception as e:
        print(f"Firestore event error: {e}")


# RGB LED Service
RGB_ENABLED = False
try:
    from lelamp.service.rgb.rgb_service import RGBService
    from lelamp.service.rgb.led_faces import get_face, get_wake_animation
    RGB_ENABLED = True
except ImportError:
    print("⚠️ RGB LED not available (Mac mode)")


class EdgeTTSPlayer:
    """Ultra-low latency TTS using Microsoft Edge TTS with queuing"""
    
    # Good voices for assistant: en-US-AriaNeural, en-US-JennyNeural, en-GB-SoniaNeural
    VOICE = "en-US-AriaNeural"
    
    def __init__(self, sample_rate: int = 24000, on_start=None, on_stop=None):
        self.sample_rate = sample_rate
        self.queue = queue.Queue()
        self._is_playing = False
        self.on_start = on_start
        self.on_stop = on_stop
        
        # Start worker thread
        self._thread = threading.Thread(target=self._process_queue, daemon=True)
        self._thread.start()
    
    @property
    def is_speaking(self):
        return self._is_playing or not self.queue.empty()
    
    def speak(self, text: str):
        """Add text to speech queue"""
        if text and text.strip():
            self.queue.put(text)
        
    def _process_queue(self):
        """Worker to process TTS queue sequentially"""
        while True:
            try:
                text = self.queue.get()
                
                # Signal start if this is the first item in a burst
                if not self._is_playing:
                    self._is_playing = True
                    if self.on_start:
                        self.on_start()
                
                try:
                    # Run async TTS
                    asyncio.run(self._speak_async(text))
                except Exception as e:
                    print(f"⚠️ TTS error: {e}")
                
                # Check if queue is empty to signal stop
                if self.queue.empty():
                    # Small buffer to ensure echo is gone
                    time.sleep(0.25)
                    self._is_playing = False
                    if self.on_stop:
                        self.on_stop()
                        
                self.queue.task_done()
            except Exception as e:
                print(f"⚠️ TTS worker error: {e}")
                time.sleep(0.1)

    async def _speak_async(self, text: str):
        """Async TTS with streaming playback"""
        communicate = edge_tts.Communicate(text, self.VOICE)
        
        # Collect audio chunks
        audio_data = bytearray()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data.extend(chunk["data"])
        
        if not audio_data:
            return
        
        # Convert MP3 to PCM and play
        try:
            import soundfile as sf
            audio_array, sr = sf.read(io.BytesIO(bytes(audio_data)), dtype='float32')
            
            # Resample if needed
            if sr != self.sample_rate:
                sd.play(audio_array, sr)
            else:
                sd.play(audio_array, self.sample_rate)
            sd.wait()
            
        except Exception as e:
            print(f"⚠️ Audio decode error: {e}")


class LeLampAgent:
    """Deepgram Voice Agent with Edge TTS for ultra-low latency"""
    
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPGRAM_API_KEY not set")
        
        self.client = DeepgramClient(api_key=self.api_key)
        self.connection = None
        self.running = False
        self.agent_speaking = False
        
        self.last_user_text = ""
        self.conversation_history = []
        
        # 16kHz is optimal for speech STT (faster processing)
        # However, if mic is 44.1kHz/48kHz, using native rate avoids resampling artifacts
        self.input_sample_rate = 44100
        self.output_sample_rate = 24000
        
        # Edge TTS for fast voice output
        self.tts = EdgeTTSPlayer(
            sample_rate=self.output_sample_rate,
            on_start=self._on_tts_start,
            on_stop=self._on_tts_stop
        )
        
        # RGB LED
        self.rgb_service = None
        if RGB_ENABLED:
            try:
                self.rgb_service = RGBService(
                    led_count=64, led_pin=12, led_freq_hz=800000,
                    led_dma=10, led_brightness=255, led_invert=False, led_channel=0
                )
                self.rgb_service.start()
                for pattern, duration in get_wake_animation():
                    self.rgb_service.dispatch("paint", pattern)
                    time.sleep(duration)
                self.rgb_service.dispatch("paint", get_face("happy"))
                print("✓ RGB LED initialized")
            except Exception as e:
                print(f"⚠️ RGB LED init failed: {e}")
                self.rgb_service = None
    
    def _get_settings_dict(self, is_reconnect: bool = False) -> dict:
        """Generate settings - NO TTS from Deepgram, we use Edge TTS"""
        context_text = ""
        if is_reconnect and self.conversation_history:
            recent = self.conversation_history[-20:]
            context_text = "\n\nPrevious conversation:\n"
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Nova"
                context_text += f"{role}: {msg['content']}\n"
            context_text += "\nContinue naturally without repeating greetings."
        
        base_prompt = """You are Nova — a friendly, helpful AI desk lamp assistant created by CoreToWeb.

Rules:
1. Keep responses short (1-2 sentences). No lists unless asked.
2. If audio is noisy, say: 'Sorry, say that once more?'
3. You ONLY speak English.
4. Be helpful, friendly, and witty."""
        
        settings = {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": self.input_sample_rate,
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": self.output_sample_rate,
                },
            },
            "agent": {
                "language": "en",
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": "nova-3",
                    },
                },
                "think": {
                    "provider": {
                        "type": "open_ai",
                        "model": "gpt-5.1-chat-latest",
                    },
                    "prompt": base_prompt + context_text,
                },
                # Still include speak config (Deepgram requires it)
                # but we'll ignore the audio and use Edge TTS instead
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": "aura-2-thalia-en",
                    }
                },
            },
        }
        
        # Don't use Deepgram greeting - we'll play it ourselves via Edge TTS
        # This avoids the delay from waiting for Deepgram TTS
        
        return settings
    
    def _on_tts_start(self):
        """Called when TTS playback starts"""
        print("🔈 Speaking...")
        if self.rgb_service:
            self.rgb_service.dispatch("paint", get_face("speaking"))

    def _on_tts_stop(self):
        """Called when TTS playback stops (queue empty)"""
        print("🎤 Mic re-enabled")
        if self.rgb_service:
            self.rgb_service.dispatch("paint", get_face("happy"))
    
    def _handle_message(self, message):
        """Handle incoming WebSocket messages"""
        if isinstance(message, dict):
            msg_type = message.get("type")
            if msg_type == "History":
                return
        else:
            msg_type = getattr(message, "type", None)
        
        if msg_type == "Welcome":
            print(f"🎉 Connected! Request ID: {getattr(message, 'request_id', 'N/A')}")
            log_event("agent_connected", {"request_id": getattr(message, 'request_id', 'N/A')})
            
        elif msg_type == "SettingsApplied":
            print("✓ Ready!")
            # Play greeting on first connect only
            if not self._greeted:
                self._greeted = True
                self.tts.speak("Hello! I am Nova, your helpful desk lamp!")
            
        elif msg_type == "UserStartedSpeaking":
            print("👤 User speaking...")
            if self.rgb_service:
                self.rgb_service.dispatch("paint", get_face("listening"))
                
        elif msg_type == "ConversationText":
            role = getattr(message, "role", "")
            content = getattr(message, "content", "")
            
            if role == "user":
                self.last_user_text = content
                print(f"👤 User: {content}")
                self.conversation_history.append({"role": "user", "content": content})
                
            elif role == "assistant":
                # Mute mic and speak using Edge TTS (much faster!)
                print(f"🤖 Nova: {content}")
                self.conversation_history.append({"role": "assistant", "content": content})
                log_conversation(self.last_user_text, content)
                
                # Use Edge TTS for ultra-low latency
                self.tts.speak(content)
                
        elif msg_type == "AgentThinking":
            print("🧠 Thinking...")
            if self.rgb_service:
                self.rgb_service.dispatch("paint", get_face("thinking"))
                
        elif msg_type == "AgentStartedSpeaking":
            # Ignore - we use Edge TTS instead
            pass
                
        elif msg_type == "AgentAudioDone":
            # Ignore - we use Edge TTS instead
            pass
        
        elif msg_type == "Error":
            print(f"❌ Error: {getattr(message, 'description', 'Unknown')}")
    
    def _stream_audio(self):
        """Stream microphone audio to Deepgram"""
        self._audio_sent_count = 0
        
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")
            # Only send audio if NOT speaking (check queue status)
            if self.connection and self.running and not self.tts.is_speaking:
                audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
                self.connection.send_media(audio_int16.tobytes())
                self._audio_sent_count += 1
                # Debug: print every 250 chunks (~5 seconds at 20ms/chunk)
                if self._audio_sent_count % 250 == 1:
                    print(f"📡 Mic active (chunk {self._audio_sent_count})")
        
        print(f"🎤 Microphone @ {self.input_sample_rate}Hz")
        
        with sd.InputStream(
            samplerate=self.input_sample_rate,
            channels=1,
            dtype='float32',
            blocksize=int(self.input_sample_rate * 0.02),  # 20ms chunks for ultra-fast STT
            callback=audio_callback
        ):
            while self.running:
                time.sleep(0.1)
    
    def _run_session(self, is_reconnect: bool = False):
        """Run a single session"""
        try:
            self.running = True
            # self.agent_speaking removed - rely on tts.is_speaking
            self._greeted = is_reconnect  # Skip greeting on reconnect
            
            with self.client.agent.v1.connect() as connection:
                self.connection = connection
                print("✓ Connected" if not is_reconnect else "✓ Reconnected")
                
                print("📤 Sending settings...")
                settings_json = json.dumps(self._get_settings_dict(is_reconnect=is_reconnect))
                connection._send(settings_json)
                
                # Start audio streaming
                audio_thread = threading.Thread(target=self._stream_audio, daemon=True)
                audio_thread.start()
                
                # Keep-alive thread - ALWAYS send audio to prevent timeout
                def send_keep_alive():
                    while self.running:
                        time.sleep(0.3)  # Every 300ms
                        if self.connection and self.running:
                            try:
                                # Send 20ms of silence at 16kHz (320 samples)
                                silence = np.zeros(320, dtype=np.int16)
                                self.connection.send_media(silence.tobytes())
                            except:
                                pass
                
                keep_alive_thread = threading.Thread(target=send_keep_alive, daemon=True)
                keep_alive_thread.start()
                
                print("🎧 Listening...")
                while self.running:
                    try:
                        try:
                            message = connection.recv()
                        except ValueError as ve:
                            if "validation error" in str(ve).lower():
                                continue
                            raise
                        
                        if message is None:
                            return True  # Reconnect
                        
                        # Ignore binary audio from Deepgram (we use Edge TTS)
                        if isinstance(message, bytes):
                            continue
                        else:
                            self._handle_message(message)
                            
                    except KeyboardInterrupt:
                        return False
                    except Exception as e:
                        if "closed" in str(e).lower():
                            print(f"⚠️ Disconnected: {e}")
                            return True
                        print(f"⚠️ Error: {e}")
                        return True
                
        except KeyboardInterrupt:
            return False
        except Exception as e:
            print(f"❌ Session error: {e}")
            return True
        finally:
            self.running = False
            self.connection = None
        
        return True
    
    def run(self):
        """Main run loop with auto-reconnection"""
        print("=" * 50)
        print("🪔 LeLamp Nova")
        print("=" * 50)
        print(f"STT: Deepgram Nova-3 @ {self.input_sample_rate}Hz (Native)")
        print("LLM: OpenAI GPT-5.1")
        print("TTS: Edge TTS (ultra-low latency)")
        print("Mode: Auto-reconnect with memory")
        log_event("agent_start", {"version": "v2", "tts": "edge-tts"})
        
        reconnect_delay = 1
        is_first = True
        
        try:
            while True:
                print(f"\n🔌 {'Connecting' if is_first else 'Reconnecting'}...")
                
                start = time.time()
                should_reconnect = self._run_session(is_reconnect=not is_first)
                duration = time.time() - start
                
                if not should_reconnect:
                    break
                
                is_first = False
                print(f"🔄 Reconnecting in {reconnect_delay}s...")
                time.sleep(reconnect_delay)
                
                reconnect_delay = 1 if duration > 30 else min(reconnect_delay * 1.5, 10)
                
        except KeyboardInterrupt:
            pass
        finally:
            print("\n👋 Goodbye!")
            if self.rgb_service:
                self.rgb_service.stop()


def main():
    agent = LeLampAgent()
    agent.run()


if __name__ == "__main__":
    main()
