#!/bin/bash
set -e

echo "🫐 LeLamp Raspberry Pi Setup"

# 1. System Dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-venv \
    python3-pip \
    ffmpeg \
    libsm6 \
    libxext6 \
    libatlas-base-dev \
    portaudio19-dev \
    libopencv-dev

# 2. Python Environment
echo "🐍 Setting up Python environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "⬇️ Installing Python packages..."
# Ensure pip is up to date
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# 3. Hardware Permissions (Motors)
echo "🔌 Configuring USB permissions..."
# Add rule for Feetech Motors (usually ttyACM0 or similar)
# Allow read/write for all users or 'dialout' group
RULE_FILE="/etc/udev/rules.d/99-feetech.rules"
if [ ! -f "$RULE_FILE" ]; then
    echo 'SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666"' | sudo tee $RULE_FILE
    # Also generic rule for common serial chips if needed
    echo 'KERNEL=="ttyACM*", MODE="0666"' | sudo tee -a $RULE_FILE
    
    sudo udevadm control --reload-rules
    sudo udevadm trigger
fi

# 4. Audio Config (Optional)
# Might need to ensure user is in 'audio' group
sudo usermod -a -G audio,dialout,video $USER

echo "✅ Setup Complete!"
echo "Run with: ./start.sh"
