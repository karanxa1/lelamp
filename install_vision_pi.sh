#!/bin/bash
echo "👁️  Installing Vision Dependencies for Pi..."

# Check for venv
if [ ! -d ".venv" ]; then
    echo "❌ No virtual environment found! Run ./setup_pi.sh first."
    exit 1
fi

PIP_CMD="./.venv/bin/pip"

# 1. Try standard mediapipe (might fail on some OS versions)
echo "Attempting standard 'mediapipe' install..."
if $PIP_CMD install mediapipe; then
    echo "✅ Standard Mediapipe installed successfully!"
    exit 0
fi

# 2. Try mediapipe-rpi4 (Community build for RPi)
echo "⚠️ Standard install failed. Attempting 'mediapipe-rpi4'..."
if $PIP_CMD install mediapipe-rpi4; then
    echo "✅ Mediapipe (rpi4 version) installed successfully!"
    exit 0
fi

# 3. Last resort: Try relaxing dependencies or older version
echo "⚠️ trying mediapipe-rpi3..."
if $PIP_CMD install mediapipe-rpi3; then
    echo "✅ Mediapipe (rpi3 version) installed successfully!"
    exit 0
fi

echo "❌ Could not install mediapipe automatically."
echo "You may need to build it from source or check python compatibility."
exit 1
