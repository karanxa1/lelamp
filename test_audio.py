"""
Test OpenRouter Audio Input API with gpt-audio-mini.
"""
import os
import wave
import math
import struct
import base64
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def generate_test_wav(filename="test_audio.wav", duration=2.0, freq=440.0):
    """Generates a simple sine wave WAV file."""
    print(f"Generating test audio file: {filename}...")
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(n_samples):
            value = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
            data = struct.pack('<h', value)
            wav_file.writeframes(data)
    
    print(f"✓ Generated {filename}")
    return filename

def encode_audio(file_path):
    """Reads and encodes audio file to base64."""
    with open(file_path, "rb") as audio_file:
        return base64.b64encode(audio_file.read()).decode("utf-8")

def test_audio_analysis():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Error: OPENROUTER_API_KEY not found in environment.")
        return

    audio_path = generate_test_wav()
    base64_audio = encode_audio(audio_path)
    
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
    
    print("Sending audio to OpenRouter (model: openai/gpt-audio-mini)...")
    
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost",
                "X-Title": "LeLamp Audio Test",
            },
            extra_body={},
            model="openai/gpt-4o-audio-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is in this audio?"
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": base64_audio,
                                "format": "wav"
                            }
                        }
                    ]
                }
            ]
        )
        
        print("\n" + "="*50)
        print("Response received:")
        print("="*50)
        print(completion.choices[0].message.content)
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ API Request Failed: {e}")

    if os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"\nCleaned up {audio_path}")

if __name__ == "__main__":
    test_audio_analysis()
