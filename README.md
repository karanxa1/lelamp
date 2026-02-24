# LeLamp Nova – AI-Powered Robotic Desk Lamp

![](./assets/images/Banner.png)

An AI-powered robotic desk lamp with real-time voice conversation, physical 5-DOF articulation, animated LED face expressions, and gesture-based hand tracking. Built with Deepgram STT, GPT-4o-mini (via OpenRouter), and Microsoft Edge TTS.

**Nova** is your friendly AI desk lamp — it listens, thinks, speaks, moves, and reacts emotionally.

---

## Features

- 🎤 **Voice Interaction** — Real-time speech-to-text via Deepgram Nova-2, streaming voice output via Edge TTS
- 💡 **8×8 LED Matrix Faces** — 10+ animated emotional expressions (happy, sad, thinking, listening, speaking, angry, love, etc.)
- 🤖 **5-DOF Robotic Arm** — Pre-recorded motor animations + smooth idle breathing animation
- 🧠 **AI Conversations** — GPT-4o-mini LLM via OpenRouter with tool calling for hardware control
- 👋 **Hand Tracking** — MediaPipe-based real-time hand following with fist gesture lock/unlock
- 📝 **Firebase Logging** — Conversations and API audit trails stored in Firestore
- 🌐 **Web Dashboard** — FastAPI control panel for RGB, animations, and chat history
- ⏰ **Alarm Service** — Set voice-triggered alarms with multi-format time parsing
- 🔍 **Web Search** — Live internet search via Serper API

---

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
# With hardware support (servos + LEDs on Pi):
uv sync --extra hardware

# Without hardware (Mac / simulation mode):
uv sync
```

### 3. Configure Environment
Create a `.env` file in the project root:
```env
OPENROUTER_API_KEY=your_openrouter_key
DEEPGRAM_API_KEY=your_deepgram_key
NOVA_DEBUG=false
```

### 4. Add Firebase Credentials
Place your Firebase service account file at:
```
firebase-credentials.json
```

### 5. Run the Agent
```bash
# Using startup script (auto-detects audio, sets ALSA):
sudo bash start.sh

# Or directly:
sudo -E uv run main.py console
```

### 6. Run the Web Dashboard (optional)
```bash
uv run web_server.py
# Access at: http://<pi-ip>:8000
```

---

## Project Structure

```
lelamp_runtime/
├── main.py                      # Main Nova voice agent (Deepgram + Edge TTS)
├── deepgram_agent.py            # Standalone Deepgram Voice Agent WebSocket client
├── web_server.py                # FastAPI dashboard + Firebase logging + WebSocket
├── start.sh                     # Startup script: auto-detects audio, configures ALSA
├── firebase-credentials.json    # Firestore service account (not committed)
├── motor_offsets.json           # Per-unit servo position calibration offsets
├── .env                         # API keys (not committed)
├── static/                      # Web dashboard frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
├── arduino/
│   └── main/
│       └── main.ino             # Arduino Nano LED bridge (Adafruit NeoPixel)
└── lelamp/
    ├── service/
    │   ├── motors/
    │   │   └── direct_motors_service.py   # Raw serial motor control (1Mbaud)
    │   ├── rgb/
    │   │   ├── rgb_service.py             # WS2812B LED control via rpi_ws281x
    │   │   └── led_faces.py               # 8×8 LED face pattern definitions
    │   ├── vision/
    │   │   └── vision_service.py          # MediaPipe hand tracking + gesture detection
    │   └── alarm/
    │       └── alarm_service.py           # Voice-triggered alarm scheduler
    ├── recordings/                        # Pre-recorded motor animations (CSV)
    └── base.py                            # ServiceBase thread management
```

---

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| **Raspberry Pi** | Pi 4B (4GB RAM) recommended |
| **Servo Motors** | 5× Feetech STS3215 (base_yaw, base_pitch, elbow_pitch, wrist_roll, wrist_pitch) |
| **LED Matrix** | 8×8 WS2812B NeoPixels (64 LEDs) |
| **Level Shifter** | SN74AHCT125N (3.3V → 5V for LED data line) |
| **Arduino** | Arduino Nano — acts as LED bridge controller |
| **Microphone** | USB PnP microphone |
| **Camera** | USB Camera (640×480) for hand tracking |
| **Speaker** | 3.5mm audio output |
| **Power** | 5V/4A (Pi + LEDs) + 7.4V (servos, separate supply) |

### Wiring Summary

| Connection | Detail |
|------------|--------|
| Pi GPIO18 → SN74AHCT125N 1A | LED data signal (3.3V input) |
| SN74AHCT125N 1Y → WS2812B DIN | LED data signal (5V output) |
| Pi USB → Feetech Servo Bus | Serial at 1,000,000 baud |
| Pi USB → Arduino Nano | Serial at 115,200 baud |
| Arduino D3 → WS2812B DIN | NeoPixel control |

---

## Motor Calibration

```bash
# Find motor USB port
ls /dev/ttyUSB* /dev/ttyACM*

# Run calibration to set motor_offsets.json
sudo -E uv run python -c "
from lelamp.service.motors.direct_motors_service import DirectMotorsService
svc = DirectMotorsService('/dev/ttyUSB0')
svc.start()
# Move lamp to desired home position manually, then save offsets
"
```

Offsets are stored in `motor_offsets.json`. Motors use these offsets as their `0°` reference for all animations.

---

## Recording New Animations

Animations are CSV files in `lelamp/recordings/`. Each row is one frame with columns: `base_yaw.pos`, `base_pitch.pos`, `elbow_pitch.pos`, `wrist_roll.pos`, `wrist_pitch.pos`.

To trigger via voice, Nova calls the `play_animation` tool and passes the CSV filename (without `.csv`).

---

## LED Face Patterns

The 8×8 matrix displays animated emotional expressions defined in `led_faces.py`:

| State | Color | Trigger |
|-------|-------|---------|
| `listening` | Cyan | User starts speaking |
| `thinking` | Purple | LLM processing |
| `speaking` | Green | Nova responding |
| `happy` | Yellow | Positive context |
| `sad` | Blue | Sad context |
| `angry` | Red | Stern context |
| `love` | Pink | Warm context |
| `idle` | Dim white | No activity |

Expressions change automatically based on conversation state via the `set_led_face` tool call.

---

## AI Tool Calls

Nova can control hardware via LLM tool calls:

| Tool | Action |
|------|--------|
| `set_volume` | Adjust speaker volume (0–100%) |
| `set_led_color` | Change LED matrix color |
| `set_led_face` | Set emotional face expression |
| `play_animation` | Play a pre-recorded motor animation |
| `start_hand_tracking` | Start camera + MediaPipe hand following |
| `stop_hand_tracking` | Stop hand tracking |
| `get_current_time` | Return system time |
| `set_alarm` | Schedule an alarm |
| `search_web` | Live search via Serper API |

---

## Auto-Start on Boot

```bash
sudo nano /etc/systemd/system/lelamp.service
```

```ini
[Unit]
Description=LeLamp Nova Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/pi/lelamp
ExecStart=/bin/bash /home/pi/lelamp/start.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable lelamp.service
sudo systemctl start lelamp.service
```

---

## Web Dashboard

Run `web_server.py` and access at `http://<pi-ip>:8000`:

- **Controls** — RGB color picker, expression buttons, play animations
- **Chat** — Text chat with Nova (OpenRouter / OpenAI backend)
- **Conversations** — View full conversation history from Firestore
- **Audit Logs** — API request log for every endpoint call

---

## API Keys Required

| Service | Purpose | Get Key |
|---------|---------|---------|
| **OpenRouter** | LLM responses (GPT-4o-mini) | [openrouter.ai](https://openrouter.ai) |
| **Deepgram** | Speech-to-text (Nova-2) | [deepgram.com](https://deepgram.com) |
| **Firebase** | Conversation + audit logging | [firebase.google.com](https://firebase.google.com) |
| **Serper** | Web search tool | [serper.dev](https://serper.dev) |

---

## Troubleshooting

### Audio Issues
```bash
# Check audio devices
aplay -l
arecord -l

# Load Pi audio driver
sudo modprobe snd_bcm2835

# Test speaker
speaker-test -D plughw:0,0 -t sine -f 440 -l 1

# Test microphone
arecord -D plughw:3,0 -r 48000 -f S16_LE -d 3 test.wav && aplay test.wav
```

### LEDs Not Working
```bash
# rpi_ws281x requires root for GPIO access
sudo -E uv run main.py console

# Check level shifter wiring:
# Pi GPIO18 (Pin 12) → SN74AHCT125N input
# SN74AHCT125N output → WS2812B DIN
```

### Servos Not Moving
```bash
# Verify USB serial port
ls /dev/ttyUSB*

# Check motor_offsets.json exists
cat motor_offsets.json

# Default baud rate is 1,000,000 — confirm servo firmware matches
```

### Hand Tracking Not Starting
```bash
# Check camera connected
ls /dev/video*

# MediaPipe requires camera at index 0 by default
# Change camera_index in VisionService if using different index
```

---

## License

MIT License — see [LICENSE](./LICENSE) for details.

---

## Made By

**Nova AI Agent** — CoreToWeb Team
