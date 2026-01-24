"""
LeLamp Web Control Panel - FastAPI Server with Firebase Firestore Logging
Controls RGB lights, motor recordings, and voice interaction.
Logs all conversations and API calls to Firebase Firestore.
"""
import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uuid

load_dotenv()

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Try to import hardware services (separate so motors work on Mac)
import glob
MOTOR_PORT = None
MOTORS_AVAILABLE = False
RGB_AVAILABLE = False

# Motors (works on Mac via USB)
try:
    from lelamp.service.motors.direct_motors_service import DirectMotorsService
    ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*')
    if ports:
        MOTOR_PORT = ports[0]
    elif os.path.exists('/dev/ttyACM0'):
        MOTOR_PORT = '/dev/ttyACM0'
    if MOTOR_PORT:
        MOTORS_AVAILABLE = True
        print(f"✓ Motor port: {MOTOR_PORT}")
except ImportError as e:
    print(f"⚠️ Motors not available: {e}")

# RGB (requires Raspberry Pi)
try:
    from lelamp.service.rgb.rgb_service import RGBService
    RGB_AVAILABLE = True
except ImportError:
    print("⚠️ RGB not available (Mac mode)")

HARDWARE_AVAILABLE = MOTORS_AVAILABLE or RGB_AVAILABLE

# Firestore Logger
class FirestoreLogger:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.session_start = datetime.now(timezone.utc)
        
    async def log_api_call(self, endpoint: str, method: str, payload: dict, response: dict, duration_ms: float):
        """Log API call to audit_logs collection"""
        try:
            doc_ref = db.collection("audit_logs").document()
            doc_ref.set({
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc),
                "endpoint": endpoint,
                "method": method,
                "payload": payload,
                "response": response,
                "duration_ms": duration_ms,
                "device": "lelamp"
            })
        except Exception as e:
            print(f"Firestore log error: {e}")
    
    async def log_conversation(self, user_input: str, ai_response: str, input_type: str = "voice"):
        """Log conversation to conversations collection"""
        try:
            doc_ref = db.collection("conversations").document()
            doc_ref.set({
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc),
                "user_input": user_input,
                "ai_response": ai_response,
                "input_type": input_type,
                "device": "lelamp"
            })
        except Exception as e:
            print(f"Firestore conversation log error: {e}")
    
    async def log_event(self, event_type: str, data: dict):
        """Log general events"""
        try:
            doc_ref = db.collection("events").document()
            doc_ref.set({
                "session_id": self.session_id,
                "timestamp": datetime.now(timezone.utc),
                "event_type": event_type,
                "data": data,
                "device": "lelamp"
            })
        except Exception as e:
            print(f"Firestore event log error: {e}")

logger = FirestoreLogger()

# Global state
class LampState:
    def __init__(self):
        self.motors_service = None
        self.rgb_service = None
        self.current_color = (255, 255, 255)
        self.is_recording = False
        self.voice_active = False
        self.connected_clients: List[WebSocket] = []
    
    async def broadcast(self, message: dict):
        for client in self.connected_clients:
            try:
                await client.send_json(message)
            except:
                pass

state = LampState()

# Pydantic models
class RGBColor(BaseModel):
    r: int
    g: int
    b: int

class RGBPattern(BaseModel):
    colors: List[List[int]]

class RecordingAction(BaseModel):
    name: str

class ConversationMessage(BaseModel):
    user_input: str
    ai_response: str
    input_type: str = "text"

class VoiceInput(BaseModel):
    audio: str  # base64 encoded audio
    format: str = "webm"

# OpenAI client for voice processing (optional)
try:
    from openai import OpenAI
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if api_key:
        openai_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
    else:
        openai_client = None
        print("⚠️ No OPENROUTER_API_KEY - chat disabled")
except ImportError:
    openai_client = None

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await logger.log_event("server_start", {"motors": MOTORS_AVAILABLE, "rgb": RGB_AVAILABLE})
    # Init motors (works on Mac via USB)
    if MOTORS_AVAILABLE and MOTOR_PORT:
        try:
            state.motors_service = DirectMotorsService(port=MOTOR_PORT, fps=30)
            state.motors_service.start()
            recordings = state.motors_service.get_available_recordings()
            print(f"✓ Motors: {len(recordings)} animations")
        except Exception as e:
            print(f"⚠️ Motors init failed: {e}")
    # Init RGB (only on Raspberry Pi)
    if RGB_AVAILABLE:
        try:
            state.rgb_service = RGBService(led_count=64, led_pin=12, led_freq_hz=800000, led_dma=10, led_brightness=255, led_invert=False, led_channel=0)
            state.rgb_service.start()
            state.rgb_service.dispatch("solid", (255, 255, 255))
            print("✓ RGB LEDs initialized")
        except Exception as e:
            print(f"⚠️ RGB init failed: {e}")
    yield
    await logger.log_event("server_stop", {})
    if state.motors_service:
        state.motors_service.stop()
    if state.rgb_service:
        state.rgb_service.stop()

app = FastAPI(title="LeLamp Control Panel", lifespan=lifespan)

# Middleware for API logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now(timezone.utc)
    response = await call_next(request)
    duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    
    # Log API calls (skip static files)
    if request.url.path.startswith("/api"):
        await logger.log_api_call(
            endpoint=request.url.path,
            method=request.method,
            payload={},  # Body already consumed
            response={"status_code": response.status_code},
            duration_ms=duration
        )
    return response

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

# RGB Endpoints
@app.post("/api/rgb/solid")
async def set_rgb_solid(color: RGBColor):
    state.current_color = (color.r, color.g, color.b)
    if state.rgb_service:
        state.rgb_service.dispatch("solid", state.current_color)
    await state.broadcast({"type": "rgb", "color": state.current_color})
    await logger.log_event("rgb_change", {"color": state.current_color})
    return {"status": "ok", "color": state.current_color}

@app.post("/api/rgb/pattern")
async def set_rgb_pattern(pattern: RGBPattern):
    colors = [tuple(c) for c in pattern.colors]
    if state.rgb_service:
        state.rgb_service.dispatch("paint", colors)
    await state.broadcast({"type": "pattern", "count": len(colors)})
    await logger.log_event("rgb_pattern", {"count": len(colors)})
    return {"status": "ok", "count": len(colors)}

@app.post("/api/rgb/off")
async def rgb_off():
    state.current_color = (0, 0, 0)
    if state.rgb_service:
        state.rgb_service.clear()
    await state.broadcast({"type": "rgb", "color": (0, 0, 0)})
    await logger.log_event("rgb_off", {})
    return {"status": "ok"}

# Recording Endpoints
@app.get("/api/recordings")
async def list_recordings():
    if state.motors_service:
        recordings = state.motors_service.get_available_recordings()
    else:
        recordings_dir = os.path.join(os.path.dirname(__file__), "lelamp", "recordings")
        recordings = []
        if os.path.exists(recordings_dir):
            for f in os.listdir(recordings_dir):
                if f.endswith(".csv"):
                    recordings.append(f[:-4])
    return {"recordings": sorted(recordings)}

@app.post("/api/recordings/play")
async def play_recording(action: RecordingAction):
    if state.motors_service:
        state.motors_service.dispatch("play", action.name)
    await state.broadcast({"type": "playing", "name": action.name})
    await logger.log_event("recording_play", {"name": action.name})
    return {"status": "ok", "playing": action.name}

# Conversation Logging
@app.post("/api/conversation")
async def log_conversation(message: ConversationMessage):
    await logger.log_conversation(message.user_input, message.ai_response, message.input_type)
    return {"status": "ok"}

# Text Chat - sends to OpenRouter and logs to Firestore
class ChatInput(BaseModel):
    message: str

@app.post("/api/chat")
async def chat(chat_input: ChatInput):
    if not openai_client:
        return {"status": "error", "error": "Chat disabled - no API key configured"}
    try:
        response = openai_client.chat.completions.create(
            model="google/gemini-2.0-flash-exp",
            messages=[
                {"role": "system", "content": "You are Nova, a friendly AI desk lamp assistant. Keep responses short and conversational."},
                {"role": "user", "content": chat_input.message}
            ]
        )
        
        ai_response = response.choices[0].message.content
        
        # Log to Firestore
        await logger.log_conversation(chat_input.message, ai_response, "text")
        
        # Broadcast to WebSocket clients
        await state.broadcast({
            "type": "new_conversation",
            "user_input": chat_input.message,
            "ai_response": ai_response
        })
        
        return {
            "status": "ok",
            "user_input": chat_input.message,
            "ai_response": ai_response
        }
        
    except Exception as e:
        await logger.log_event("chat_error", {"error": str(e)})
        return {"status": "error", "error": str(e)}


# Get conversation history
@app.get("/api/conversations")
async def get_conversations(limit: int = 50):
    try:
        docs = db.collection("conversations").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
        conversations = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            data["timestamp"] = data["timestamp"].isoformat() if data.get("timestamp") else None
            conversations.append(data)
        return {"conversations": conversations}
    except Exception as e:
        return {"error": str(e), "conversations": []}

# Get audit logs
@app.get("/api/audit-logs")
async def get_audit_logs(limit: int = 100):
    try:
        docs = db.collection("audit_logs").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(limit).stream()
        logs = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            data["timestamp"] = data["timestamp"].isoformat() if data.get("timestamp") else None
            logs.append(data)
        return {"logs": logs}
    except Exception as e:
        return {"error": str(e), "logs": []}

# Status
@app.get("/api/status")
async def get_status():
    return {
        "hardware": HARDWARE_AVAILABLE,
        "rgb": state.current_color,
        "recording": state.is_recording,
        "voice": state.voice_active,
        "session_id": logger.session_id
    }

# WebSocket
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    state.connected_clients.append(websocket)
    await logger.log_event("websocket_connect", {"client_count": len(state.connected_clients)})
    try:
        await websocket.send_json({
            "type": "init",
            "hardware": HARDWARE_AVAILABLE,
            "rgb": state.current_color,
            "session_id": logger.session_id
        })
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "conversation":
                await logger.log_conversation(
                    data.get("user_input", ""),
                    data.get("ai_response", ""),
                    data.get("input_type", "text")
                )
    except WebSocketDisconnect:
        state.connected_clients.remove(websocket)
        await logger.log_event("websocket_disconnect", {"client_count": len(state.connected_clients)})

if __name__ == "__main__":
    import uvicorn
    print("🔥 Firebase Firestore logging enabled")
    print(f"📝 Session ID: {logger.session_id}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
