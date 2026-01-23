"""
Voice-to-Voice Streaming Chat with OpenRouter.
Records mic → Streams to AI → Streams audio back through speakers.
"""
import os
import wave
import base64
import pyaudio
import tempfile
import threading
import queue
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000
RECORD_SECONDS = 5

class AudioPlayer:
    """Plays audio chunks as they arrive (streaming playback)."""
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.playing = False
        self.p = None
        self.stream = None
        
    def start(self):
        self.playing = True
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
        self.thread = threading.Thread(target=self._play_loop)
        self.thread.start()
        
    def _play_loop(self):
        while self.playing:
            try:
                chunk = self.audio_queue.get(timeout=0.1)
                if chunk:
                    self.stream.write(chunk)
            except queue.Empty:
                continue
                
    def add_chunk(self, audio_data):
        self.audio_queue.put(audio_data)
        
    def stop(self):
        self.playing = False
        if self.thread:
            self.thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()

def record_audio():
    p = pyaudio.PyAudio()
    print(f"\n🎤 Recording for {RECORD_SECONDS} seconds... Speak now!")
    
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = [stream.read(CHUNK) for _ in range(int(RATE / CHUNK * RECORD_SECONDS))]
    
    print("✓ Recording complete!")
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        filename = f.name
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    return filename

def voice_chat():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found!")
        return

    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    print("="*50)
    print("🗣️  Voice-to-Voice Streaming Chat")
    print("="*50)
    
    while True:
        input("\nPress Enter to start recording (Ctrl+C to exit)...")
        
        # 1. Record from mic
        audio_path = record_audio()
        with open(audio_path, "rb") as f:
            base64_audio = base64.b64encode(f.read()).decode("utf-8")
        os.remove(audio_path)
        
        print("📤 Streaming to AI...")
        
        try:
            # 2. Stream request with audio output
            response = client.chat.completions.create(
                extra_headers={"HTTP-Referer": "http://localhost", "X-Title": "VoiceChat"},
                model="openai/gpt-4o-audio-preview",
                modalities=["text", "audio"],
                audio={"voice": "alloy", "format": "pcm16"},
                stream=True,  # Required for audio output
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Respond conversationally to what I said."},
                        {"type": "input_audio", "input_audio": {"data": base64_audio, "format": "wav"}}
                    ]
                }]
            )
            
            # 3. Start audio player for streaming playback
            player = AudioPlayer()
            player.start()
            
            text_parts = []
            audio_received = False
            
            print("🤖 AI responding (streaming)...")
            
            for chunk in response:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                
                # Collect text
                if hasattr(delta, 'content') and delta.content:
                    text_parts.append(delta.content)
                
                # Stream audio chunks immediately
                if hasattr(delta, 'audio') and delta.audio:
                    if hasattr(delta.audio, 'data') and delta.audio.data:
                        audio_data = base64.b64decode(delta.audio.data)
                        player.add_chunk(audio_data)
                        audio_received = True
            
            # Wait for playback to finish
            import time
            time.sleep(0.5)
            player.stop()
            
            # Print text response
            if text_parts:
                print(f"\n💬 Text: {''.join(text_parts)}")
            
            if not audio_received:
                print("⚠️ No audio chunks received")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    try:
        voice_chat()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
