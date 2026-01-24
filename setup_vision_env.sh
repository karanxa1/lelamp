#!/bin/bash
set -e

echo "🔮 Setting up Vision Environment (Python 3.11)..."

# 1. Install Python 3.11 if missing
if ! command -v python3.11 &> /dev/null; then
    echo "⬇️ Installing Python 3.11..."
    sudo apt-get update
    sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
fi

# 2. Create Venv explicitly with Python 3.11
echo "🧹 Recreating venv..."
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Upgrade pip
pip install --upgrade pip

# 4. Install Dependencies (Order Matters)
echo "📦 Installing libraries..."
# Protobuf first
pip install "protobuf==3.20.3"
# MediaPipe next
pip install "mediapipe==0.10.9"
# Rest from file
pip install -r requirements.txt

echo "✅ Environment Ready!"
echo "👉 Run with: ./start.sh"
