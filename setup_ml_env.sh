#!/bin/bash
set -e

echo "🤖 Setting up TFLite/MediaPipe Vision Environment (.venv_ml)..."

# 1. Install Python 3.11
if ! command -v python3.11 &> /dev/null; then
    echo "⬇️ Installing Python 3.11..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

# 2. Create Venv
echo "🧹 Creating environment..."
rm -rf .venv_ml
python3.11 -m venv .venv_ml
source .venv_ml/bin/activate

# 3. Install Core ML Dependencies
echo "📦 Installing TFLite/MediaPipe..."
pip install --upgrade pip
# Force Protobuf 3.20.x for MediaPipe compatibility
pip install "protobuf<4.0.0,>=3.20.0"
pip install "mediapipe==0.10.9"

# 4. Install Application Dependencies
pip install \
    "deepgram-sdk>=3.0.0" \
    "edge-tts>=6.1.9" \
    "sounddevice>=0.5.2" \
    "firebase-admin>=6.0.0" \
    "numpy<2.0.0" \
    "feetech-servo-sdk>=1.0.0" \
    "rpi-ws281x" \
    "adafruit-circuitpython-neopixel" \
    "pyaudio>=0.2.14" \
    pyserial \
    requests \
    python-dotenv \
    soundfile \
    "hf_transfer" \
    "huggingface_hub" \
    "lerobot @ git+https://github.com/huggingface/lerobot"

echo "✅ ML Vision Environment Ready at .venv_ml"
