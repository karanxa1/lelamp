"""
Deepgram Voice Agent Client

A simple WebSocket client for Deepgram's Voice Agent API that handles
STT, LLM, and TTS in a single connection.
"""

import asyncio
import json
import os
import struct
from typing import Callable, Optional
import websockets
import sounddevice as sd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

# Firebase logging
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-credentials.json")
    firebase_admin.initialize_app(cred)
db = firestore.client()


def log_conversation(user_input: str, ai_response: str):
    """Log conversation to Firestore"""
    try:
        db.collection("conversations").add({
            "timestamp": datetime.now(timezone.utc),
            "user_input": user_input,
            "ai_response": ai_response,
            "input_type": "voice",
            "device": "lelamp",
            "source": "deepgram_agent"
        })
        print("✓ Firestore: Logged conversation")
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


class DeepgramVoiceAgent:
    """Deepgram Voice Agent WebSocket client"""
    
    def __init__(
        self,
        api_key: str,
        prompt: str = "You are Nova, a friendly AI desk lamp assistant.",
        greeting: str = "Hello! I am Nova, your helpful desk lamp!",
        stt_model: str = "nova-3",
        tts_model: str = "aura-2-thalia-en",
        llm_model: str = "gpt-4o-mini",
        input_sample_rate: int = 16000,
        output_sample_rate: int = 24000,
        on_user_speaking: Optional[Callable] = None,
        on_agent_speaking: Optional[Callable] = None,
        on_agent_done: Optional[Callable] = None,
    ):
        self.api_key = api_key
        self.prompt = prompt
        self.greeting = greeting
        self.stt_model = stt_model
        self.tts_model = tts_model
        self.llm_model = llm_model
        self.input_sample_rate = input_sample_rate
        self.output_sample_rate = output_sample_rate
        
        # Callbacks for LED reactions
        self.on_user_speaking = on_user_speaking
        self.on_agent_speaking = on_agent_speaking
        self.on_agent_done = on_agent_done
        
        self.ws = None
        self.running = False
        self.last_user_text = ""
        self.last_agent_text = ""
        
        # Audio buffers
        self.audio_output_buffer = []
        
    def _get_settings(self) -> dict:
        """Generate settings message for Deepgram Voice Agent"""
        return {
            "type": "Settings",
            "audio": {
                "input": {
                    "encoding": "linear16",
                    "sample_rate": self.input_sample_rate
                },
                "output": {
                    "encoding": "linear16",
                    "sample_rate": self.output_sample_rate
                }
            },
            "agent": {
                "listen": {
                    "provider": {
                        "type": "deepgram",
                        "model": self.stt_model
                    }
                },
                "think": {
                    "provider": {
                        "type": "open_ai",
                        "model": self.llm_model
                    },
                    "prompt": self.prompt
                },
                "speak": {
                    "provider": {
                        "type": "deepgram",
                        "model": self.tts_model
                    }
                },
                "greeting": self.greeting
            }
        }
    
    async def _handle_message(self, message):
        """Handle incoming WebSocket messages"""
        if isinstance(message, bytes):
            # Binary audio data from agent
            self.audio_output_buffer.append(message)
            return
            
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")
            
            if msg_type == "Welcome":
                print(f"🎉 Connected! Request ID: {data.get('request_id')}")
                log_event("agent_connected", {"request_id": data.get("request_id")})
                
            elif msg_type == "SettingsApplied":
                print("✓ Settings applied")
                
            elif msg_type == "UserStartedSpeaking":
                print("👤 User speaking...")
                if self.on_user_speaking:
                    self.on_user_speaking()
                    
            elif msg_type == "ConversationText":
                role = data.get("role", "")
                content = data.get("content", "")
                if role == "user":
                    self.last_user_text = content
                    print(f"👤 User: {content}")
                elif role == "assistant":
                    self.last_agent_text = content
                    print(f"🤖 Nova: {content}")
                    # Log conversation when agent responds
                    log_conversation(self.last_user_text, content)
                    
            elif msg_type == "AgentThinking":
                print(f"🧠 Thinking: {data.get('content', '')}")
                
            elif msg_type == "AgentStartedSpeaking":
                latency = data.get("total_latency", 0)
                print(f"🔊 Agent speaking (latency: {latency:.2f}s)")
                if self.on_agent_speaking:
                    self.on_agent_speaking()
                    
            elif msg_type == "AgentAudioDone":
                print("✓ Agent finished speaking")
                if self.on_agent_done:
                    self.on_agent_done()
                # Play buffered audio
                await self._play_audio()
                    
            elif msg_type == "Error":
                print(f"❌ Error: {data.get('description')} ({data.get('code')})")
                
            elif msg_type == "Warning":
                print(f"⚠️ Warning: {data.get('description')}")
                
        except json.JSONDecodeError:
            pass
    
    async def _play_audio(self):
        """Play buffered audio"""
        if not self.audio_output_buffer:
            return
            
        # Combine all audio chunks
        audio_data = b''.join(self.audio_output_buffer)
        self.audio_output_buffer.clear()
        
        # Convert to numpy array (16-bit signed int, little endian)
        audio_array = np.frombuffer(audio_data, dtype=np.int16)
        
        # Normalize to float32 [-1, 1]
        audio_float = audio_array.astype(np.float32) / 32768.0
        
        # Play audio
        try:
            sd.play(audio_float, self.output_sample_rate, blocking=False)
        except Exception as e:
            print(f"Audio playback error: {e}")
    
    async def _send_audio(self):
        """Capture and send microphone audio"""
        def audio_callback(indata, frames, time, status):
            if status:
                print(f"Audio input status: {status}")
            if self.ws and self.running:
                # Convert float32 to int16
                audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
                asyncio.run_coroutine_threadsafe(
                    self.ws.send(audio_int16.tobytes()),
                    self.loop
                )
        
        print(f"🎤 Starting microphone (sample rate: {self.input_sample_rate})")
        
        with sd.InputStream(
            samplerate=self.input_sample_rate,
            channels=1,
            dtype='float32',
            blocksize=int(self.input_sample_rate * 0.1),  # 100ms chunks
            callback=audio_callback
        ):
            while self.running:
                await asyncio.sleep(0.1)
    
    async def run(self):
        """Main run loop"""
        self.running = True
        self.loop = asyncio.get_event_loop()
        
        url = "wss://agent.deepgram.com/v1/agent/converse"
        
        print("🔌 Connecting to Deepgram Voice Agent...")
        log_event("agent_start", {"model": self.llm_model})
        
        try:
            async with websockets.connect(
                url,
                additional_headers={"Authorization": f"Token {self.api_key}"}
            ) as ws:
                self.ws = ws
                
                # Send settings
                await ws.send(json.dumps(self._get_settings()))
                print("📤 Settings sent")
                
                # Start audio capture task
                audio_task = asyncio.create_task(self._send_audio())
                
                # Handle incoming messages
                try:
                    async for message in ws:
                        await self._handle_message(message)
                except websockets.exceptions.ConnectionClosed:
                    print("Connection closed")
                finally:
                    self.running = False
                    audio_task.cancel()
                    
        except Exception as e:
            print(f"Connection error: {e}")
            self.running = False
    
    def stop(self):
        """Stop the agent"""
        self.running = False


async def main():
    """Run the Deepgram Voice Agent"""
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ DEEPGRAM_API_KEY not set!")
        return
    
    agent = DeepgramVoiceAgent(
        api_key=api_key,
        prompt="""You are Nova — a friendly, helpful AI desk lamp assistant. You speak in a warm, conversational tone.

Rules:
1. Keep responses short and conversational. No lists unless asked.
2. If audio is noisy, say: 'Sorry, say that once more?'
3. You ONLY speak English.
4. You were created by CoreToWeb students and team.""",
        greeting="Hello! I am Nova, your helpful desk lamp created by CoreToWeb!",
        tts_model="aura-2-thalia-en",
        llm_model="gpt-4o-mini",
    )
    
    try:
        await agent.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
