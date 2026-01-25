#!/bin/bash
set -e

echo "🔮 Setting up Dedicated Vision Environment (.venv_vision)..."

# 1. Install Python 3.11 System-wide
if ! command -v python3.11 &> /dev/null; then
    echo "⬇️ Installing Python 3.11..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

# 2. Create independent venv (NOT managed by uv)
echo "🧹 Creating .venv_vision..."
rm -rf .venv_vision
python3.11 -m venv .venv_vision
source .venv_vision/bin/activate

# 3. Install EXACT compatible versions
echo "📦 Installing libraries..."
pip install --upgrade pip
pip install "protobuf==3.20.3"
pip install "mediapipe==0.10.9"

# 4. Install other deps manually to avoid conflict
# 4. Install other deps manually to avoid conflict
# Use quotes for versions with < or >
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

# 5. FORCE downgrade protobuf to fix MediaPipe conflict
# Many packages (like firebase-admin or google-api-core) pull in new protobuf
echo "🔧 Forcing Protobuf Downgrade..."
pip install "protobuf==3.20.3" --force-reinstall

echo "✅ Vision Environment Ready at .venv_vision"
