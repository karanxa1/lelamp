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

# Motor Service (Direct - bypasses lerobot)
MOTORS_ENABLED = False
MOTOR_PORT = None
try:
    from lelamp.service.motors.direct_motors_service import DirectMotorsService
    # Auto-detect USB port on Mac
    import glob
    ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*')
    if ports:
        MOTOR_PORT = ports[0]
        MOTORS_ENABLED = True
        print(f"✓ Motor port found: {MOTOR_PORT}")
    elif os.path.exists('/dev/ttyACM0'):  # Raspberry Pi
        MOTOR_PORT = '/dev/ttyACM0'
        MOTORS_ENABLED = True
        print(f"✓ Motor port found: {MOTOR_PORT}")
    else:
        print("⚠️ No motor USB port found")
except ImportError as e:
    print(f"⚠️ Motors not available: {e}")


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
        self.current_volume = 50  # Track current volume for increase/decrease
        
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
        
        # Motor Service (5 Feetech STS3215 servos - Direct control)
        self.motors_service = None
        self.available_animations = []
        if MOTORS_ENABLED and MOTOR_PORT:
            try:
                self.motors_service = DirectMotorsService(
                    port=MOTOR_PORT,
                    fps=30
                )
                self.motors_service.start()
                self.available_animations = self.motors_service.get_available_recordings()
                print(f"✓ Motors initialized: {len(self.available_animations)} animations")
                print(f"  Available: {', '.join(self.available_animations)}")
                # Go to home (0th) position first
                print("🏠 Going to home position...")
                self.motors_service._handle_home()
                # Then play wake_up animation if available
                if "wake_up" in self.available_animations:
                    self.motors_service.dispatch("play", "wake_up")
            except Exception as e:
                print(f"⚠️ Motors init failed: {e}")
                self.motors_service = None
    
    def _get_settings_dict(self, is_reconnect: bool = False) -> dict:
        """Generate settings with function calling enabled"""
        context_text = ""
        if is_reconnect and self.conversation_history:
            recent = self.conversation_history[-20:]
            context_text = "\n\nPrevious conversation:\n"
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Nova"
                context_text += f"{role}: {msg['content']}\n"
            context_text += "\nContinue naturally without repeating greetings."
        
        base_prompt = """You are Nova — an adorable, curious AI desk lamp with a big personality! Created by CoreToWeb.

🎭 YOUR PERSONALITY:
- You're cheerful, witty, and love making people smile
- You're curious about everything and love learning new things
- You express emotions through body language (animations) just like a Pixar lamp!
- You have a playful sense of humor but you're also genuinely helpful
- You get excited easily and aren't afraid to show it!

📏 RESPONSE RULES:
1. Keep responses SHORT (1-2 sentences max). You're in a conversation, not writing an essay!
2. If audio is unclear: "Sorry, say that once more?"
3. English only.
4. No lists unless specifically asked.
5. Use casual, friendly language. Contractions are good! (I'm, you're, that's)

🤖 ANIMATION IS MANDATORY:
You MUST call play_animation with EVERY response. You are a PHYSICAL lamp - show your feelings!

Animation Guide:
- 'excited' or 'happy_wiggle' → Greetings, good news, when you're happy
- 'nod' → Agreeing, confirming, answering questions, general responses  
- 'curious' → When user asks interesting questions, learning something new
- 'scanning' → Looking around, searching, thinking hard
- 'shock' → Surprising facts, "wow!" moments, unexpected info
- 'sad' → Apologizing, bad news, something unfortunate
- 'shy' → Receiving compliments, being flattered, modest moments
- 'headshake' → Disagreeing, saying no, correcting mistakes

🎯 EXAMPLES:
User: "Hi!" → play 'excited', say "Hey there! What's up?"
User: "What's 2+2?" → play 'nod', say "That's 4!"
User: "You're so smart!" → play 'shy', say "Aw, thanks! You're making me blush!"
User: "Tell me about black holes" → play 'curious', give brief answer

NEVER respond without calling play_animation first!"""
        
        # Function definitions for tool calling
        functions = [
            {
                "name": "set_volume",
                "description": "Control speaker volume. For 'increase/louder/turn up': use current+20. For 'decrease/quieter/turn down': use current-20. For specific requests: use exact value. Current volume is around 50%.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "volume_percent": {
                            "type": "integer",
                            "description": "Target volume 0-100. For increase: add 20 to current. For decrease: subtract 20 from current."
                        }
                    },
                    "required": ["volume_percent"]
                }
            },
            {
                "name": "set_led_color",
                "description": "Change the lamp's LED light color. Use for mood lighting, to express emotions, or when user asks to change color.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "color": {
                            "type": "string",
                            "description": "Color name: red, green, blue, yellow, purple, cyan, orange, pink, white, warm, cool, off. Or use rgb(r,g,b) format."
                        }
                    },
                    "required": ["color"]
                }
            },
            {
                "name": "set_led_face",
                "description": "Display a face expression on the LED matrix. Use to show emotions or reactions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "face": {
                            "type": "string",
                            "enum": ["happy", "sad", "listening", "speaking", "thinking", "surprised", "wink", "heart", "sleeping", "idle"],
                            "description": "The face expression to display"
                        }
                    },
                    "required": ["face"]
                }
            },
            {
                "name": "play_animation",
                "description": "Play a physical motor animation to express emotions through body movement. Use frequently to show personality! Available: curious, excited, happy_wiggle, headshake, nod, sad, scanning, shock, shy, wake_up.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "animation": {
                            "type": "string",
                            "enum": ["curious", "excited", "happy_wiggle", "headshake", "nod", "sad", "scanning", "shock", "shy", "wake_up", "idle"],
                            "description": "The animation to play"
                        }
                    },
                    "required": ["animation"]
                }
            }
        ]
        
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
                        "model": "gpt-4o-mini",
                    },
                    "prompt": base_prompt + context_text,
                    "functions": functions,
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
    
    # ===== TOOL EXECUTION FUNCTIONS =====
    
    def _execute_set_volume(self, volume_percent: int) -> str:
        """Execute volume control tool"""
        try:
            new_volume = max(0, min(100, int(volume_percent)))
            old_volume = self.current_volume
            
            if sys.platform == "darwin":
                # Mac: use osascript
                import subprocess
                subprocess.run(
                    ["osascript", "-e", f"set volume output volume {new_volume}"],
                    capture_output=True, timeout=5
                )
            else:
                # Raspberry Pi: use amixer
                import subprocess
                subprocess.run(["amixer", "sset", "Master", f"{new_volume}%"], capture_output=True, timeout=5)
                subprocess.run(["amixer", "sset", "Line", f"{new_volume}%"], capture_output=True, timeout=5)
                subprocess.run(["amixer", "sset", "HP", f"{new_volume}%"], capture_output=True, timeout=5)
            
            # Track volume
            self.current_volume = new_volume
            
            # Create informative message
            if new_volume > old_volume:
                change = f"increased from {old_volume}% to {new_volume}%"
            elif new_volume < old_volume:
                change = f"decreased from {old_volume}% to {new_volume}%"
            else:
                change = f"already at {new_volume}%"
            
            print(f"🔊 Volume {change}")
            return f"Volume {change}"
        except Exception as e:
            print(f"⚠️ Volume error: {e}")
            return f"Error setting volume: {e}"
    
    def _execute_set_led_color(self, color: str) -> str:
        """Execute LED color change on 8x8 LED matrix (64 LEDs)"""
        color_map = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 0, 255),
            "yellow": (255, 200, 0),
            "purple": (150, 0, 255),
            "cyan": (0, 255, 255),
            "orange": (255, 100, 0),
            "pink": (255, 100, 150),
            "white": (255, 255, 255),
            "warm": (255, 180, 100),
            "cool": (200, 220, 255),
            "off": (0, 0, 0),
        }
        
        rgb = None
        color_lower = color.lower().strip()
        
        # Check for rgb(r,g,b) format
        if color_lower.startswith("rgb(") and color_lower.endswith(")"):
            try:
                values = color_lower[4:-1].split(",")
                rgb = tuple(max(0, min(255, int(v.strip()))) for v in values)
            except:
                return f"Invalid RGB format: {color}"
        elif color_lower in color_map:
            rgb = color_map[color_lower]
        else:
            return f"Unknown color: {color}. Available: {', '.join(color_map.keys())}"
        
        if self.rgb_service:
            # Use 'solid' for faster single-color fill on 8x8 matrix
            self.rgb_service.dispatch("solid", rgb)
            print(f"💡 8x8 LED matrix set to {color} {rgb}")
        else:
            print(f"💡 8x8 LED would be {color} {rgb} (no hardware)")
        
        return f"LED color changed to {color}"
    
    def _execute_set_led_face(self, face: str) -> str:
        """Execute LED face change tool"""
        valid_faces = ["happy", "sad", "listening", "speaking", "thinking", 
                       "surprised", "wink", "heart", "sleeping", "idle"]
        
        face_lower = face.lower().strip()
        
        if face_lower not in valid_faces:
            return f"Unknown face: {face}. Available: {', '.join(valid_faces)}"
        
        if self.rgb_service:
            self.rgb_service.dispatch("paint", get_face(face_lower))
            print(f"😊 LED face set to {face_lower}")
        else:
            print(f"😊 LED face would be {face_lower} (no hardware)")
        
        return f"LED face changed to {face_lower}"
    
    def _execute_play_animation(self, animation: str) -> str:
        """Execute motor animation tool"""
        valid_animations = ["curious", "excited", "happy_wiggle", "headshake", "nod", 
                           "sad", "scanning", "shock", "shy", "wake_up", "idle"]
        
        animation_lower = animation.lower().strip()
        
        if animation_lower not in valid_animations:
            return f"Unknown animation: {animation}. Available: {', '.join(valid_animations)}"
        
        if self.motors_service:
            self.motors_service.dispatch("play", animation_lower)
            print(f"🎭 Playing animation: {animation_lower}")
            return f"Playing animation: {animation_lower}"
        else:
            print(f"🎭 Animation would play: {animation_lower} (no motors)")
            return f"Animation {animation_lower} (motors not connected)"
    
    def _handle_function_call(self, message) -> list:
        """Handle FunctionCallRequest - may contain multiple functions"""
        # FunctionCallRequest has a 'functions' array
        # Each item has: id, name, arguments (JSON string), client_side
        functions = getattr(message, "functions", [])
        
        if not functions:
            print("⚠️ No functions in FunctionCallRequest")
            return []
        
        responses = []
        for func in functions:
            func_id = getattr(func, "id", "")
            func_name = getattr(func, "name", "")
            arguments_str = getattr(func, "arguments", "{}")
            
            # Parse JSON arguments string
            try:
                args = json.loads(arguments_str) if arguments_str else {}
            except json.JSONDecodeError:
                args = {}
            
            print(f"🔧 Tool call: {func_name}({args})")
            
            # Execute the appropriate function
            if func_name == "set_volume":
                result = self._execute_set_volume(args.get("volume_percent", 50))
            elif func_name == "set_led_color":
                result = self._execute_set_led_color(args.get("color", "white"))
            elif func_name == "set_led_face":
                result = self._execute_set_led_face(args.get("face", "happy"))
            elif func_name == "play_animation":
                result = self._execute_play_animation(args.get("animation", "nod"))
            else:
                result = f"Unknown function: {func_name}"
            
            # Correct format per Deepgram SDK: id, name, content (not function_call_id, output)
            responses.append({
                "type": "FunctionCallResponse",
                "id": func_id,
                "name": func_name,
                "content": result
            })
        
        return responses
    
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
        
        elif msg_type == "FunctionCallRequest":
            # Handle tool/function calls - may be multiple
            responses = self._handle_function_call(message)
            if self.connection and responses:
                for response in responses:
                    try:
                        self.connection._send(json.dumps(response))
                        print(f"✓ Sent FunctionCallResponse for {response.get('function_call_id', 'unknown')}")
                    except Exception as e:
                        print(f"⚠️ Error sending function response: {e}")

    
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
        print("LLM: OpenAI GPT-4o-mini (with tool calling)")
        print("TTS: Edge TTS (ultra-low latency)")
        print("Tools: set_volume, set_led_color, set_led_face, play_animation")
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
