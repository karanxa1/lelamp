"""
Test OpenRouter Audio API with live microphone input.
Records from your mic, sends to OpenRouter, and prints the response.
"""
import os
import wave
import base64
import pyaudio
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 5

def record_audio(filename="recording.wav"):
    """Records audio from your microphone."""
    p = pyaudio.PyAudio()
    
    print(f"\n🎤 Recording for {RECORD_SECONDS} seconds... Speak now!")
    
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    
    for _ in range(int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    print("✓ Recording complete!")
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
    
    return filename

def encode_audio(file_path):
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

def analyze_audio():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found!")
        return

    audio_path = record_audio()
    base64_audio = encode_audio(audio_path)
    
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    
    print("\n📤 Sending to OpenRouter (gpt-4o-audio-preview)...")
    
    try:
        response = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "http://localhost", "X-Title": "LeLamp"},
            model="openai/gpt-4o-audio-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "What did I say? Transcribe and describe."},
                    {"type": "input_audio", "input_audio": {"data": base64_audio, "format": "wav"}}
                ]
            }]
        )
        
        print("\n" + "="*50)
        print("🤖 Response:")
        print("="*50)
        print(response.choices[0].message.content)
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    if os.path.exists(audio_path):
        os.remove(audio_path)

if __name__ == "__main__":
    analyze_audio()
