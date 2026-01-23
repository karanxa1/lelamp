from dotenv import load_dotenv
import argparse
import subprocess

from livekit import agents, api, rtc
from livekit.agents import (
    AgentSession, 
    Agent, 
    RoomInputOptions,
    function_tool,
    tts as agents_tts,
)
import logging
from livekit.plugins import (
    noise_cancellation,
    deepgram,
)
from lelamp.service.rgb.rgb_service import RGBService
from lelamp.service.rgb.led_faces import get_face, get_wake_animation, FACE_PATTERNS
from kokoro_tts import KokoroTTS
from mimo_llm import MimoLLM
from typing import Union
import os
from threading import Lock

load_dotenv()

# Firebase Admin SDK for logging conversations
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()

_greeted_once = False
_greet_lock = Lock()

def log_conversation_to_firestore(user_input: str, ai_response: str, input_type: str = "voice"):
    """Log conversation to Firestore"""
    try:
        db.collection("conversations").add({
            "timestamp": datetime.now(timezone.utc),
            "user_input": user_input,
            "ai_response": ai_response,
            "input_type": input_type,
            "device": "lelamp",
            "source": "stt_tts"
        })
        print(f"✓ Firestore: Logged conversation")
    except Exception as e:
        print(f"Firestore error: {e}")

def log_event_to_firestore(event_type: str, data: dict):
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

# Configure verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logging.getLogger("livekit.agents").setLevel(logging.DEBUG)
logging.getLogger("livekit.plugins.openai").setLevel(logging.DEBUG)
logging.getLogger("livekit.plugins.deepgram").setLevel(logging.DEBUG)
logging.getLogger("livekit.plugins.elevenlabs").setLevel(logging.DEBUG)

# Agent Class
class LeLamp(Agent):
    def __init__(self, port: str = "/dev/ttyACM0", lamp_id: str = "lelamp") -> None:
        super().__init__(instructions="""You are Nova — a friendly, helpful AI desk lamp assistant. You speak in a warm, conversational tone.

Rules:
1. Keep responses short and conversational. No lists unless asked.
2. If audio is noisy, say: 'Sorry, say that once more?'
3. You ONLY speak English.
4. You can control your volume with set_volume function.
5. You were created by CoreToWeb students and team.

        """)
        
        # Initialize RGB LED service
        self.rgb_service = RGBService(
            led_count=64,
            led_pin=12,
            led_freq_hz=800000,
            led_dma=10,
            led_brightness=255,
            led_invert=False,
            led_channel=0
        )
        self.rgb_service.start()
        
        # Play wake animation
        for pattern, duration in get_wake_animation():
            self.rgb_service.dispatch("paint", pattern)
            import time
            time.sleep(duration)
        
        # Set to happy face
        self.rgb_service.dispatch("paint", get_face("happy"))
        
        # Motor hardware not available - commented out
        # self.motors_service = MotorsService(port=port, lamp_id=lamp_id, fps=30)
        # self.motors_service.start()
        # self.motors_service.dispatch("play", "wake_up")
        
        self._set_system_volume(100)
        print("LeLamp initialized (RGB enabled, motors disabled)")
        log_event_to_firestore("agent_init", {"lamp_id": lamp_id})

    def _set_system_volume(self, volume_percent: int):
        try:
            subprocess.run(["sudo", "-u", "pi", "amixer", "sset", "Line", f"{volume_percent}%"], capture_output=True, text=True, timeout=5)
            subprocess.run(["sudo", "-u", "pi", "amixer", "sset", "Line DAC", f"{volume_percent}%"], capture_output=True, text=True, timeout=5)
            subprocess.run(["sudo", "-u", "techspark", "amixer", "sset", "HP", f"{volume_percent}%"], capture_output=True, text=True, timeout=5)
        except Exception:
            pass

    def mute_mic(self):
        try:
            subprocess.run(["amixer", "set", "Capture", "nocap"], capture_output=True, timeout=2)
            subprocess.run(["amixer", "set", "Mic", "mute"], capture_output=True, timeout=2)
        except Exception:
            pass
    
    def unmute_mic(self):
        try:
            subprocess.run(["amixer", "set", "Capture", "cap"], capture_output=True, timeout=2)
            subprocess.run(["amixer", "set", "Mic", "unmute"], capture_output=True, timeout=2)
        except Exception:
            pass

    @function_tool
    async def set_volume(self, volume_percent: int) -> str:
        """
        Control system audio volume. Use when users ask to be louder or quieter.
        Args:
            volume_percent: Volume level as percentage (0-100). 0=mute, 50=half volume, 100=max
        """
        print(f"LeLamp: set_volume function called with volume: {volume_percent}%")
        log_event_to_firestore("volume_change", {"volume": volume_percent})
        try:
            if not 0 <= volume_percent <= 100:
                return "Error: Volume must be between 0 and 100 percent"
            self._set_system_volume(volume_percent)
            return f"Set volume to {volume_percent}%"
        except subprocess.TimeoutExpired:
            return "Error: Volume control command timed out"
        except FileNotFoundError:
            return "Error: amixer command not found on system"
        except Exception as e:
            return f"Error controlling volume: {str(e)}"

# Entry to the agent
async def entrypoint(ctx: agents.JobContext):
    global _greeted_once
    agent = LeLamp(lamp_id="lelamp")
    
    session = AgentSession(
        llm=MimoLLM(
            model="mimo-v2-flash",
            api_key=os.getenv("MIMO_API_KEY"),
        ),
        stt=deepgram.STT(
            api_key=os.getenv("DEEPGRAM_API_KEY"),
        ),
        tts=agents_tts.StreamAdapter(
            tts=KokoroTTS(
                model_path="kokoro-v1.0.onnx",
                voices_path="voices-v1.0.bin",
                voice="af_heart",
                speed=1.0,
            ),
            text_pacing=True,
        ),
    )

    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await agent.set_volume(100)
    log_event_to_firestore("session_start", {"room": str(ctx.room.name)})
    
    # Half-duplex mode with LED face reactions
    @session.on("agent_started_speaking")
    def on_agent_speaking():
        agent.mute_mic()
        agent.rgb_service.dispatch("paint", get_face("speaking"))
        print("Nova: Speaking... (mic muted)")
    
    @session.on("agent_stopped_speaking")
    def on_agent_stopped():
        agent.unmute_mic()
        agent.rgb_service.dispatch("paint", get_face("listening"))
        print("Nova: Listening... (mic active)")
    
    # Log conversations to Firestore
    last_user_input = {"text": ""}
    
    @session.on("user_speech_committed")
    def on_user_speech(event):
        if hasattr(event, 'text') and event.text:
            last_user_input["text"] = event.text
            print(f"👤 User (STT): {event.text}")
    
    @session.on("agent_speech_committed") 
    def on_agent_speech(event):
        if hasattr(event, 'text') and event.text:
            log_conversation_to_firestore(
                user_input=last_user_input["text"],
                ai_response=event.text,
                input_type="voice"
            )
            print(f"🤖 Nova (TTS): {event.text}")
    
    greet_now = False
    with _greet_lock:
        if not _greeted_once:
            _greeted_once = True
            greet_now = True
    if greet_now:
        await session.generate_reply(
            instructions="""You are Nova, a friendly AI desk lamp assistant. When you wake up, say 'Hello! I am Nova, your helpful desk lamp created by CoreToWeb!' Keep responses concise and conversational. You remember context from our conversation.""",
            allow_interruptions=False,
        )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint, num_idle_processes=1))
