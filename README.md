# LeLamp Runtime - Nova AI Voice Assistant

![](./assets/images/Banner.png)

An AI-powered robotic desk lamp with voice interaction, animated expressions, and RGB LED faces. Built with LiveKit Agents, Kokoro TTS, and MIMO LLM.

**Nova** is your friendly AI desk lamp assistant, created by CoreToWeb!

## Features

- 🎤 **Voice Interaction** - Real-time speech recognition (Deepgram) and local TTS (Kokoro)
- 💡 **8x8 LED Matrix Faces** - Animated expressions that react to conversation state
- 🤖 **5-DOF Robotic Arm** - Pre-recorded motor animations for expressions
- 🧠 **AI Responses** - MIMO v2 Flash LLM for intelligent conversations
- 📝 **Firebase Logging** - All conversations stored in Firestore
- 🌐 **Web Dashboard** - Control panel for RGB, expressions, and chat history

## Quick Start (Raspberry Pi)

### 1. Install UV & Clone
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc
git clone <your-repo-url> ~/lelamp
cd ~/lelamp
```

### 2. Install Dependencies
```bash
# With hardware support:
uv sync --extra hardware

# Without hardware (simulation):
uv sync
```

### 3. Download TTS Models
```bash
wget -4 https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
wget -4 https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

### 4. Configure Environment
Create `.env` file:
```env
MIMO_API_KEY=your_mimo_api_key
LIVEKIT_URL=wss://your-livekit-url
LIVEKIT_API_KEY=your_livekit_key
LIVEKIT_API_SECRET=your_livekit_secret
DEEPGRAM_API_KEY=your_deepgram_key
```

### 5. Configure Audio (Raspberry Pi)
```bash
# Create ALSA config for USB mic + 3.5mm output
cat > ~/.asoundrc << 'EOF'
pcm.!default {
    type asym
    playback.pcm "plughw:0,0"
    capture.pcm "plughw:3,0"
}
ctl.!default {
    type hw
    card 0
}
EOF

# Load audio driver if needed
sudo modprobe snd_bcm2835
```

### 6. Run the Agent
```bash
sudo -E ~/.local/bin/uv run main.py console
```

## Project Structure

```
lelamp_runtime/
├── main.py                     # Main voice agent (Nova)
├── smooth_animation.py         # Alternative agent with smooth motor animations
├── kokoro_tts.py              # Local Kokoro ONNX TTS plugin
├── mimo_llm.py                # MIMO v2 Flash LLM client
├── voice_chat.py              # Standalone voice-to-voice chat
├── web_server.py              # FastAPI dashboard + Firebase logging
├── firebase-credentials.json  # Firestore service account
├── static/                    # Web dashboard files
│   ├── index.html
│   ├── app.js
│   └── style.css
└── lelamp/                    # Hardware control package
    ├── follower/              # Robot arm follower controller
    ├── leader/                # Teleoperator for teaching movements
    ├── service/
    │   ├── motors/            # Motor animation service
    │   └── rgb/               # LED control + face patterns
    │       ├── rgb_service.py
    │       └── led_faces.py   # 8x8 LED face patterns
    ├── recordings/            # Pre-recorded motor animations
    ├── calibrate.py           # Motor calibration
    ├── record.py              # Record new animations
    └── replay.py              # Replay animations
```

## Hardware Requirements

| Component | Details |
|-----------|---------|
| **Raspberry Pi** | Pi 4 or Pi 5 recommended |
| **Motors** | 5x Feetech STS3215 servos |
| **LED Matrix** | 8x8 WS2812B NeoPixels (64 LEDs) |
| **Microphone** | USB PnP Sound Device |
| **Speaker** | 3.5mm audio output |

## Motor Calibration

```bash
# Find your motor port
uv run lerobot-find-port

# Calibrate motors
sudo uv run -m lelamp.calibrate --id lelamp --port /dev/ttyACM0
```

## Recording New Animations

```bash
# Record a movement sequence
uv run -m lelamp.record --id lelamp --port /dev/ttyACM0 --name my_animation

# Replay it
uv run -m lelamp.replay --id lelamp --port /dev/ttyACM0 --name my_animation
```

## LED Face Patterns

The 8x8 LED matrix displays animated faces:

| State | Description | Color |
|-------|-------------|-------|
| `listening` | Wide eyes, waiting for input | Cyan |
| `speaking` | Mouth open animation | Green |
| `happy` | Smile face | Yellow |
| `thinking` | Squinting | Purple |
| `idle` | Gentle breathing | Dim white |

Faces automatically change based on Nova's conversation state.

## Auto-Start on Boot

```bash
sudo nano /etc/systemd/system/lelamp.service
```

Add:
```ini
[Unit]
Description=LeLamp Nova Service
After=network.target

[Service]
Type=simple
User=techspark
WorkingDirectory=/home/techspark/techspark/lelamp
ExecStart=/usr/bin/sudo -E /home/techspark/.local/bin/uv run main.py console
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lelamp.service
sudo systemctl start lelamp.service
```

## Web Dashboard

Access at `http://<pi-ip>:8000` when running `web_server.py`:

- **Controls** - RGB color picker, expression buttons, chat
- **Conversations** - View chat history from Firestore
- **Audit Logs** - API request logging

## API Keys Required

| Service | Purpose | Get Key |
|---------|---------|---------|
| **MIMO API** | LLM responses | [mimo.dev](https://mimo.dev) |
| **LiveKit** | Voice rooms | [livekit.io](https://livekit.io) |
| **Deepgram** | Speech-to-text | [deepgram.com](https://deepgram.com) |
| **Firebase** | Conversation logging | [firebase.google.com](https://firebase.google.com) |

## Troubleshooting

### Audio Issues
```bash
# Check audio devices
aplay -l
arecord -l

# Load audio driver
sudo modprobe snd_bcm2835

# Test speaker
speaker-test -D plughw:0,0 -t sine -f 440 -l 1

# Test microphone
arecord -D plughw:3,0 -r 48000 -f S16_LE -d 3 test.wav
aplay test.wav
```

### LED Not Working
```bash
# Run with sudo for GPIO access
sudo uv run main.py console
```

### TTS Slow on Pi
Kokoro TTS uses CPU inference. First response may take 3-5 seconds on Pi 4.

## License

See [LeLamp repository](https://github.com/humancomputerlab/LeLamp) for licensing.

## Credits

- **LeLamp Hardware**: [Human Computer Lab](https://www.humancomputerlab.com)
- **Nova AI Agent**: CoreToWeb Team
- **Kokoro TTS**: [thewh1teagle](https://github.com/thewh1teagle/kokoro-onnx)
