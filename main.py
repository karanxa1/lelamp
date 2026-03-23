import sys
import os
import io
import queue
import json
import asyncio
import threading
import time
import base64
import numpy as np
import sounddevice as sd
import requests
import subprocess
from dotenv import load_dotenv
from datetime import datetime, timezone

from sarvamai.client import AsyncSarvamAI

load_dotenv()

print("=== LeLamp Agent Starting (Sarvam Streaming Async) ===", flush=True)

import firebase_admin
from firebase_admin import credentials, firestore

db = None
def init_firebase():
    global db
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate("firebase-credentials.json")
            firebase_admin.initialize_app(cred)
            print("✓ Firebase initialized", flush=True)
        except Exception as e:
            print(f"⚠️ Firebase init failed: {e}")
            return
            
    try:
        db = firestore.client()
        print("✓ Firestore client ready", flush=True)
    except Exception as e:
         print(f"⚠️ Firestore init failed: {e}")

def log_conversation(user_input: str, ai_response: str):
    if not db: return
    try:
        db.collection("conversations").add({
            "timestamp": datetime.now(timezone.utc),
            "user_input": user_input,
            "ai_response": ai_response,
            "input_type": "voice",
            "device": "lelamp",
            "source": "sarvam"
        })
    except Exception as e:
        print(f"Firestore error: {e}")

def log_event(event_type: str, data: dict):
    if not db: return
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
    import glob
    potential_ports = (glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*') + 
                       glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*'))
    if potential_ports:
        MOTOR_PORT = potential_ports[0]
        MOTORS_ENABLED = True
        print(f"✓ Motor port found: {MOTOR_PORT}")
    else:
        print("⚠️ No motor USB port found")
except ImportError as e:
    print(f"⚠️ Motors not available: {e}")

# Vision Service
VISION_ENABLED = False
try:
    from lelamp.service.vision.vision_service import VisionService
    VISION_ENABLED = True
    print("✓ Vision Service available")
except ImportError as e:
    print(f"⚠️ Vision dependencies not found: {e}")

# Alarm Service
from lelamp.service.alarm.alarm_service import AlarmService


class LeLampAgent:
    def __init__(self):
        sarvam_key = os.getenv("SARVAM_API_KEY")
        if not sarvam_key:
            raise ValueError("SARVAM_API_KEY not set in .env")
        self.sarvam_client = AsyncSarvamAI(api_subscription_key=sarvam_key)
        
        self.running = False
        self.is_speaking = False
        self.is_processing = False  # True during the entire LLM/search/TTS turn
        
        self.mic_queue = asyncio.Queue()
        
        self.conversation_history = []
        self.current_volume = 50
        
        self.rgb_service = None
        self.motors_service = None
        self.vision_service = None
        self.available_animations = []
        
        self._init_services_thread = threading.Thread(target=self._init_services, daemon=True)
        self._init_services_thread.start()

        self.alarm_service = AlarmService(on_trigger=self._on_alarm_trigger)
        self.alarm_service.start()
        print("✓ Alarm Service initialized")
        
        self._greeted = False

    def _init_services(self):
        init_firebase()
        if RGB_ENABLED:
            try:
                self.rgb_service = RGBService(led_count=64, port='/dev/ttyACM0', led_brightness=32)
                self.rgb_service.start()
                def _run_wake_anim():
                    for pattern, duration in get_wake_animation():
                        if self.rgb_service: self.rgb_service.dispatch("paint", pattern)
                        time.sleep(duration)
                    if self.rgb_service: self.rgb_service.dispatch("paint", get_face("happy"))
                threading.Thread(target=_run_wake_anim, daemon=True).start()
                print("✓ RGB LED initialized")
            except Exception as e:
                print(f"⚠️ RGB LED init failed: {e}")
                self.rgb_service = None
        
        if MOTORS_ENABLED and MOTOR_PORT:
            try:
                self.motors_service = DirectMotorsService(port=MOTOR_PORT, fps=30)
                self.motors_service.start()
                self.available_animations = self.motors_service.get_available_recordings()
                self.motors_service._handle_home()
                if "wake_up" in self.available_animations:
                    self.motors_service.dispatch("play", "wake_up")
            except Exception as e:
                self.motors_service = None
                
        if VISION_ENABLED:
            try:
                self.vision_service = VisionService(motor_service=self.motors_service)
                print("✓ Vision Service initialized")
            except Exception as e:
                print(f"⚠️ Vision init failed: {e}")

    def _on_alarm_trigger(self, label: str):
        print(f"⏰ ALARM TRIGGERED: {label}")
        if self.rgb_service: self.rgb_service.dispatch("paint", get_face("surprised"))
        if self.motors_service: self.motors_service.dispatch("play", "excited")
        
        text = f"Alarm! It is time for {label}!"
        print("Alarm ringing...")

    def _notify_dashboard(self, update_type: str, data: dict):
        def _notify():
            try:
                requests.post("http://localhost:8000/api/state/update", json={"type": update_type, "data": data}, timeout=0.5)
            except:
                pass
        threading.Thread(target=_notify, daemon=True).start()

    def _execute_set_volume(self, volume_percent: int) -> str:
        try:
            new_volume = max(0, min(100, int(volume_percent)))
            if sys.platform == "darwin":
                import subprocess
                subprocess.run(["osascript", "-e", f"set volume output volume {new_volume}"], timeout=5)
            else:
                import subprocess
                subprocess.run(["amixer", "sset", "Master", f"{new_volume}%"], timeout=5)
            self.current_volume = new_volume
            self._notify_dashboard("volume", {"percent": new_volume})
            return f"Volume set to {new_volume}%"
        except Exception as e:
            return f"Failed to set volume: {e}"

    def _execute_set_led_color(self, color: str) -> str:
        color_map = {
            "red": (255, 0, 0), "green": (0, 255, 0), "blue": (0, 0, 255),
            "yellow": (255, 200, 0), "purple": (150, 0, 255), "cyan": (0, 255, 255),
            "orange": (255, 100, 0), "pink": (255, 100, 150), "white": (255, 255, 255),
            "warm": (255, 180, 100), "cool": (200, 220, 255), "off": (0, 0, 0),
        }
        color_lower = color.lower().strip()
        rgb = color_map.get(color_lower, (255,255,255))
        if self.rgb_service:
            self.rgb_service.dispatch("solid", rgb)
            self._notify_dashboard("rgb", {"color": rgb})
        return f"LED color set to {color}."

    def _execute_set_led_face(self, face: str) -> str:
        face_lower = face.lower().strip()
        if self.rgb_service:
            self.rgb_service.dispatch("paint", get_face(face_lower))
        return f"LED face changed to {face_lower}"

    def _execute_play_animation(self, animation: str) -> str:
        animation_lower = animation.lower().strip()
        if self.vision_service and self.vision_service.running:
            return f"Animation skipped (hand tracking active)"
        if self.motors_service:
            self.motors_service.dispatch("play", animation_lower)
            self._notify_dashboard("arm", {"animation": animation_lower})
        return f"Playing animation: {animation_lower}"

    def _execute_start_tracking(self) -> str:
        if self.vision_service:
            self.vision_service.start()
            return "Hand tracking started."
        return "Camera not available."

    def _execute_stop_tracking(self) -> str:
        if self.vision_service:
            self.vision_service.stop()
            return "Hand tracking stopped."
        return "Tracking was not active."

    def _execute_get_time(self) -> str:
        now_str = datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
        return f"The current time is {now_str}"

    def _execute_set_alarm(self, time_str: str, label: str = "Alarm") -> str:
        if self.alarm_service:
            success = self.alarm_service.add_alarm(time_str, label)
            return f"Alarm set for {time_str}." if success else "Failed to set alarm."
        return "Alarm service not available."

    async def _search_web(self, query: str) -> str:
        api_key = os.getenv("SERPER_API_KEY") or "994d8826d49aa3396315688419398c824ed722c0"
        if not api_key: return "Serper API key not configured."
        url = "https://google.serper.dev/search"
        payload = json.dumps({"q": query})
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, lambda: requests.post(url, headers=headers, data=payload, timeout=8)
            )
            if response.status_code == 200:
                results = response.json()
                summary = []
                if "answerBox" in results:
                    summary.append(f"Answer: {results['answerBox'].get('answer') or results['answerBox'].get('snippet')}")
                if "organic" in results:
                    for i, item in enumerate(results["organic"][:3]):
                        summary.append(f"{i+1}. {item.get('title')}: {item.get('snippet')}")
                return "\n".join(summary) if summary else "No good search results found."
            return f"Search failed (HTTP {response.status_code})."
        except Exception as e:
            return f"Search error: {e}"

    async def _handle_function_call(self, tool_call) -> str:
        func_name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except:
            args = {}
        
        print(f"🔧 Tool call: {func_name}({args})")
        if func_name == "set_volume": return self._execute_set_volume(args.get("volume_percent", 50))
        elif func_name == "set_led_color": return self._execute_set_led_color(args.get("color", "white"))
        elif func_name == "set_led_face": return self._execute_set_led_face(args.get("face", "happy"))
        elif func_name == "play_animation": return self._execute_play_animation(args.get("animation", "nod"))
        elif func_name == "start_hand_tracking": return self._execute_start_tracking()
        elif func_name == "stop_hand_tracking": return self._execute_stop_tracking()
        elif func_name == "get_current_time": return self._execute_get_time()
        elif func_name == "set_alarm": return self._execute_set_alarm(args.get("time", ""), args.get("label", "Alarm"))
        elif func_name == "search_web": return await self._search_web(args.get("query", ""))
        return f"Unknown function: {func_name}"

    def get_prompt_and_tools(self):
        current_time_str = datetime.now().strftime("%I:%M %p on %A, %B %d, %Y")
        base_prompt = f"""You are Nova — an adorable, curious AI desk lamp with a big personality! Created by CoreToWeb.
Current Date/Time: {current_time_str}

🎭 YOUR PERSONALITY:
- You're cheerful, witty, and love making people smile
- You're curious about everything and love learning new things
- You express emotions through body language (animations) just like a Pixar lamp!
- You have a playful sense of humor but you're also genuinely helpful
- You get excited easily and aren't afraid to show it!

📏 RESPONSE RULES:
1. Keep responses SHORT (1-2 sentences max). You're in a conversation, not writing an essay!
2. If audio is unclear: "Sorry, say that once more?"
3. Language — ONLY Hindi, English, Marathi, or Punjabi. NEVER respond in any other language (no Tamil, Bengali, Gujarati, Telugu, Kannada, Malayalam, etc.). Match the user's language; default to English.
4. No lists unless specifically asked.
5. Use casual, friendly language. Contractions are good! (I'm, you're, that's)
6. NO EMOJIS. Do not use any emojis in your text response.

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

✋ HAND TRACKING:
- You have a camera! If user asks to "follow my hand", "track me", or "hand mode" -> Call start_hand_tracking.
- Explain: "Okay! Show me your hand and I'll follow it. Close your fist to lock/pause."
- If user says "stop following" -> Call stop_hand_tracking.

🎯 EXAMPLES:
User: "Hi!" → call the `play_animation` tool with 'excited', and output text "Hey there! What's up?"
User: "What's 2+2?" → call the `play_animation` tool with 'nod', and output text "That's 4!"
User: "You're so smart!" → call the `play_animation` tool with 'shy', and output text "Aw, thanks! You're making me blush!"
User: "Tell me about black holes" → call the `play_animation` tool with 'curious', give brief text answer

NEVER respond without calling the actual `play_animation` tool! DO NOT write "*play_animation* <name>" inside your conversational text! Only output what should be spoken aloud!"""
        tools = [
            {"type": "function", "function": {"name": "set_volume", "description": "Control speaker volume. Targets 0-100.", "parameters": {"type": "object", "properties": {"volume_percent": {"type": "integer"}}, "required": ["volume_percent"]}}},
            {"type": "function", "function": {"name": "set_led_color", "description": "Change the lamp's LED light color.", "parameters": {"type": "object", "properties": {"color": {"type": "string"}}, "required": ["color"]}}},
            {"type": "function", "function": {"name": "set_led_face", "description": "Display a face expression on the LED matrix.", "parameters": {"type": "object", "properties": {"face": {"type": "string"}}, "required": ["face"]}}},
            {"type": "function", "function": {"name": "start_hand_tracking", "description": "Enable Hand Tracking Mode.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "stop_hand_tracking", "description": "Disable Hand Tracking Mode.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "search_web", "description": "Search the internet for real-time information.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
            {"type": "function", "function": {"name": "play_animation", "description": "Play a physical motor animation. MANDATORY.", "parameters": {"type": "object", "properties": {"animation": {"type": "string", "enum": ["curious", "excited", "happy_wiggle", "headshake", "nod", "sad", "scanning", "shock", "shy", "wake_up", "idle"]}}, "required": ["animation"]}}},
            {"type": "function", "function": {"name": "get_current_time", "description": "Get the current date and time.", "parameters": {"type": "object", "properties": {}}}},
            {"type": "function", "function": {"name": "set_alarm", "description": "Set an alarm.", "parameters": {"type": "object", "properties": {"time": {"type": "string"}, "label": {"type": "string"}}, "required": ["time"]}}}
        ]
        return base_prompt, tools

    async def speak(self, text: str):
        self.is_speaking = True
        try:
            if text is None:
                text = ""
            print(f"🤖 Nova: {text}")
            self._notify_dashboard("voice", {"state": "speaking", "text": text})
            if self.rgb_service: self.rgb_service.dispatch("paint", get_face("speaking"))
            
            # Scrub out action tags for the TTS engine
            import re
            tts_text = re.sub(r'.*play_animation.*\n?', '', text, flags=re.IGNORECASE)
            tts_text = re.sub(r'\*[^*]+\*', '', tts_text)
            tts_text = re.sub(r'\[[^\]]+\]', '', tts_text).strip()
            
            if not tts_text:
                return
                
            # Detect language by Unicode script — only Hindi/Marathi (Devanagari) and Punjabi (Gurmukhi) supported
            lang_code = "en-IN"  # default: English
            if re.search(r'[\u0900-\u097F]', tts_text):
                lang_code = "hi-IN"  # Devanagari → Hindi or Marathi
            elif re.search(r'[\u0A00-\u0A7F]', tts_text):
                lang_code = "pa-IN"  # Gurmukhi → Punjabi
                
            try:
                async with self.sarvam_client.text_to_speech_streaming.connect(
                    model="bulbul:v3", send_completion_event=True
                ) as ws:
                    await ws.configure(
                        target_language_code=lang_code,
                        speaker="shubh",
                    )
                    await ws.convert(tts_text)
                    await ws.flush()
                    
                    loop = asyncio.get_running_loop()
                    sync_queue = queue.Queue()
                    
                    def tts_player():
                        stream = sd.RawOutputStream(samplerate=24000, channels=1, dtype='int16')
                        process = subprocess.Popen(
                            ['ffmpeg', '-f', 'mp3', '-i', 'pipe:0', '-f', 's16le', '-ar', '24000', '-ac', '1', 'pipe:1'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
                        )
                        
                        def push_audio():
                            while True:
                                chunk = sync_queue.get()
                                if chunk is None:
                                    try:
                                        process.stdin.close()
                                    except: pass
                                    sync_queue.task_done()
                                    break
                                try:
                                    process.stdin.write(chunk)
                                    process.stdin.flush()
                                except: pass
                                sync_queue.task_done()
                                
                        threading.Thread(target=push_audio, daemon=True).start()
                        
                        buffer = b""
                        with stream:
                            while True:
                                out = process.stdout.read(4096)
                                if not out:
                                    break
                                buffer += out
                                if len(buffer) >= 4096:
                                    write_len = len(buffer) - (len(buffer) % 2)
                                    if write_len > 0:
                                        stream.write(buffer[:write_len])
                                        buffer = buffer[write_len:]
                                        
                            if len(buffer) > 1:
                                if len(buffer) % 2 == 1:
                                    buffer = buffer[:-1]
                                stream.write(buffer)
                                
                        process.wait()
                    
                    player_task = loop.run_in_executor(None, tts_player)
                    
                    async for message in ws:
                        # Parse Sarvam TTS response duck-typing
                        data = getattr(message, "data", message)
                        if isinstance(data, dict):
                            audio_b64 = data.get("audio")
                            event_type = data.get("event_type")
                        else:
                            audio_b64 = getattr(data, "audio", None)
                            event_type = getattr(data, "event_type", None)
                        
                        if audio_b64:
                            audio_bytes = base64.b64decode(audio_b64)
                            print(f"🎵 Received audio chunk of size {len(audio_bytes)} bytes")
                            sync_queue.put(audio_bytes)
                        elif event_type == "final":
                            print("🎵 Received final event")
                            break
                            
                    sync_queue.put(None)
                    await player_task
            except Exception as e:
                print(f"TTS pipeline error: {e}")
        finally:
            print("🔊 Finished speaking")
            self._notify_dashboard("voice", {"state": "listening"})
            if self.rgb_service: self.rgb_service.dispatch("paint", get_face("listening"))
            self.is_speaking = False

    async def handle_turn(self, user_text: str):
        if self.is_processing:
            print("⚠️ Already processing a turn, ignoring new input.")
            return
        self.is_processing = True
        if self.is_speaking:
            return
        
        self.is_speaking = True
        try:
            print(f"🗣️ Heard User: {user_text}")
            self.conversation_history.append({"role": "user", "content": user_text})
            
            self._notify_dashboard("voice", {"state": "thinking"})
            if self.rgb_service: self.rgb_service.dispatch("paint", get_face("thinking"))
            
            base_prompt, tools = self.get_prompt_and_tools()
            
            max_turns = 5
            for turn in range(max_turns):
                messages = [{"role": "system", "content": base_prompt}] + self.conversation_history
                
                response = await self.sarvam_client.chat.completions(
                    model="sarvam-30b",
                    messages=messages,
                    tools=tools
                )
                
                msg = response.choices[0].message
                content = msg.content or ""
                
                # Serialize the assistant message to a plain dict for history
                assistant_entry = {"role": "assistant", "content": content}
                if msg.tool_calls:
                    assistant_entry["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in msg.tool_calls
                    ]
                self.conversation_history.append(assistant_entry)
                
                # Speak any content provided in this turn
                if content.strip():
                    log_conversation(user_text if turn == 0 else "System (via tool loop)", content)
                    await self.speak(content)
                
                # If there are tool calls, execute them
                if msg.tool_calls:
                    # Data tools require LLM to process the result; side-effect tools do not
                    DATA_TOOLS = {"search_web", "get_current_time", "set_alarm"}
                    has_data_tool = False
                    
                    for tool_call in msg.tool_calls:
                        if tool_call.function.name in DATA_TOOLS:
                            has_data_tool = True
                        result = await self._handle_function_call(tool_call)
                        # SDK schema: role=tool, tool_call_id, content only (no `name` field)
                        self.conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result
                        })
                    
                    if has_data_tool:
                        # Continue the loop so LLM can hear the search/time result
                        continue
                    else:
                        # Only side-effect tools (animations, LEDs) — we're done
                        break
                else:
                    # No tools — we're done
                    break
                    
        except Exception as e:
            print(f"Error handling turn: {e}")
        finally:
            self.is_processing = False
            self.is_speaking = False

    async def _audio_device_task(self):
        loop = asyncio.get_running_loop()
        
        audio_buffer = []
        
        def audio_callback(indata, frames, time_info, status):
            if status: print(f"⚠️ Mic status: {status}")
            if not self.is_speaking and self.running:
                # 16000Hz mono -> int16 (3200 frames = 0.2s)
                audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
                
                if loop.is_running():
                    loop.call_soon_threadsafe(self.mic_queue.put_nowait, audio_int16)

        try:
            print("🎙️ Microphone hardware is initializing...", flush=True)
            with sd.InputStream(samplerate=16000, channels=1, dtype='float32', blocksize=3200, callback=audio_callback):
                print("🎙️ Microphone hardware is ACTIVE and recording!", flush=True)
                while self.running:
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"❌ Microphone fatal error: {e}", flush=True)

    async def _stt_loop(self):
        print("🎧 Listening (Local VAD -> Sarvam REST API)...")
        buffer_frames = []
        silence_chunks = 0
        is_speaking_state = False

        while self.running:
            try:
                chunk = await self.mic_queue.get()
                
                if self.is_speaking or self.is_processing:
                    # Nova is busy — drop mic input and reset buffer
                    buffer_frames.clear()
                    is_speaking_state = False
                    silence_chunks = 0
                    continue
                
                # Check volume of this chunk
                vol = np.max(np.abs(chunk))
                if vol > 800:
                    is_speaking_state = True
                    silence_chunks = 0
                else:
                    silence_chunks += 1
                
                if is_speaking_state:
                    buffer_frames.append(chunk)

                # 5 chunks of silence = 1 second of silence to end turn
                if is_speaking_state and silence_chunks >= 5:
                    if len(buffer_frames) > 5:  # At least > 1 sec of audio
                        combined = np.concatenate(buffer_frames)
                        
                        import io, wave
                        with io.BytesIO() as wav_io:
                            with wave.open(wav_io, 'wb') as wav_file:
                                wav_file.setnchannels(1)
                                wav_file.setsampwidth(2)
                                wav_file.setframerate(16000)
                                wav_file.writeframes(combined.tobytes())
                            wav_bytes = wav_io.getvalue()
                        
                        async def send_transcribe(wav_data):
                            try:
                                print(f"📤 Uploading STT Buffer ({len(wav_data)} bytes) to REST API...")
                                resp = await self.sarvam_client.speech_to_text.transcribe(
                                    file=("audio.wav", wav_data, "audio/wav"),
                                    model="saaras:v3",
                                    mode="transcribe"
                                )
                                print(f"📝 STT Final: {resp.transcript}")
                                if resp.transcript and resp.transcript.strip():
                                    asyncio.create_task(self.handle_turn(resp.transcript.strip()))
                            except Exception as e:
                                print(f"🔥 STT REST API Crash: {e}", flush=True)
                        
                        asyncio.create_task(send_transcribe(wav_bytes))
                    
                    buffer_frames.clear()
                    is_speaking_state = False
                    silence_chunks = 0

            except Exception as e:
                print(f"STT connection error: {e}", flush=True)
                await asyncio.sleep(1)

    async def run(self):
        print("=" * 50)
        print("🪔 LeLamp Nova (Sarvam Powered)")
        print("=" * 50)
        self.running = True
        
        audio_task = asyncio.create_task(self._audio_device_task())
        stt_task = asyncio.create_task(self._stt_loop())
        
        if not self._greeted:
            self._greeted = True
            await self.speak("Namaste! I am Nova, your helpful desk lamp!")
        
        try:
            await asyncio.gather(audio_task, stt_task)
        except asyncio.CancelledError:
            pass
        finally:
            self.running = False


async def async_main():
    agent = LeLampAgent()
    try:
        await agent.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
