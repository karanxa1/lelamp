# 🪔 LeLamp Nova - Project Summary (0 to 100)

## 1. Project Vision
**LeLamp Nova** is an interactive, animated AI desk lamp that feels alive. Unlike a static smart speaker, Nova expresses personality through physical movement, light, and sound. It combines the helpfulness of a voice assistant with the charm of a Pixar-like character.

*   **Personality:** Cheerful, curious, and expressive.
*   **Interaction:** Voice (Conversation), Vision (Hand Following), and Body Language (Motor Animations).

---

## 2. System Architecture

### 🧠 The Brain (`main.py`)
The core runtime is a Python application that orchestrates three main loops:
1.  **Voice Loop:**
    *   **Ear (STT):** Deepgram Nova-2 @ 16kHz (Optimized for speed). Listens to microphone audio.
    *   **Brain (LLM):** OpenAI GPT-4o-mini. Decan handle conversation AND control hardware via **Tool Calling**.
    *   **Voice (TTS):** Edge TTS (Microsoft). Ultra-low latency speech generation.
2.  **Motor Loop:** Controls the physical robot arm (5 Motors) to play animations or follow targets.
3.  **Vision Loop:** (Mac Only) Tracks the user's hand using MediaPipe to physically look at/follow them.

### 🛠️ Hardware Stack
*   **Host:**
    *   **Development:** macOS (M1/M2/M3) - Supports Vision & High Performance.
    *   **Deployment:** Raspberry Pi 4/5 - Optimized for Headless running (Vision disabled to save resources).
*   **Motors:** Beetech/Feetech STS3215 Serial Bus Servos (High precision, feedback capable).
    *   5 Degrees of Freedom: Base Yaw, Base Pitch, Elbow, Wrist Roll, Wrist Pitch.
*   **Visual Output:**
    *   **Matrix:** 8x8 RGB LED Grid (The "Face"). Displays emotions (Happy, Sad, Wink).
    *   **Ring:** RGB Ring (The "Mood"). Ambient lighting.
*   **Audio:**
    *   USB Microphone (ReSpeaker / Generic).
    *   Speaker (3.5mm / USB).
*   **Camera:** USB Webcam (Logitech / Mac Built-in).

---

## 3. Key Features

### 🗣️ Voice Interaction
*   **Fast Response:** Optimized with 16kHz audio pipeline and 300ms endpointing (ignores background noise, replies faster).
*   **Personality:** Nova prompts are tuned to be short, witty, and casually friendly ("No essays!").
*   **Function Calling:** The LLM can "use tools" to control the physical world:
    *   `set_led_color("red")`
    *   `set_volume(80)`
    *   `set_alarm("7:00 AM")`
    *   `get_current_time()`

### 🎭 Physical Animation
*   **Library:** Pre-recorded animations stored as CSV files (motion capture style).
    *   *Examples:* `nod`, `headshake`, `excited`, `curious`, `shy`.
*   **Live Idle:** When nothing is happening, the lamp gently "breathes" (subtle sine-wave movement) so it never looks dead.
*   **Contextual:** The generic "play_animation" tool lets the AI choose how to react (e.g., getting a compliment -> plays `shy`).

### ✋ Hand Tracking (Vision)
*   **Follow Mode:** The lamp physically tracks your hand position in 3D space.
*   **Gestures:**
    *   **Open Hand:** "I see you, I will follow you."
    *   **Closed Fist:** "Pause/Lock." (Stops movement so you can inspect it).
*   **Safety:** Vision is restricted to macOS for performance stability.

---

## 4. Application Flow

1.  **Startup:**
    *   Loads Env Vars (`.env`).
    *   Connects to Motors via USB Serial (`/dev/cu.usbmodem...`).
    *   Initializes Firebase (for logging).
    *   Plays "Wake Up" animation.
2.  **Listening:**
    *   Streams Microphone audio to Deepgram.
    *   Detects VAD (Voice Activity) -> Stops listening.
3.  **Thinking:**
    *   Sends transcript to GPT-4o-mini.
    *   **DECISION:** Does user need a tool? (e.g. "Turn red") -> call tool -> get result -> generate response.
    *   **OR:** Just chat? -> generate text response.
4.  **Acting:**
    *   **Sound:** Streams Edge TTS audio to speaker ("Hey there!").
    *   **Body:** Plays random or chosen animation (e.g. `happy_wiggle`).
    *   **Face:** LED Matrix creates "Speaking" face.

---

## 5. Setup & Wiring

### Wiring (See `WIRING_GUIDE.md`)
*   **Power:** 12V 4A Supply (Motors need high current).
*   **Data:** TTL/USB Debugger connects Data wire to Pi/Mac USB.
*   **Daisy Chain:** Motors connected in series (ID 1 to ID 5).

### Code Structure
*   `main.py`: The entry point.
*   `lelamp/service/motors/`: Direct Serial control logic.
*   `lelamp/service/vision/`: CV logic (TFLite Hand model).
*   `lelamp/service/rgb/`: LED Matrix & Ring control.
*   `recordings/`: Animation CSV files.

---

## 6. Current Status (0 to 100)
*   **[100%] Core Platform:** Mic, Speaker, LLM, TTS are robust.
*   **[100%] Motors:** Smooth movement, recording playback, home position.
*   **[100%] Vision:** Hand tracking works, axes inverted correctly, gesture locking fixed.
*   **[90%] Interaction:** Latency optimized to <1s.
*   **[80%] Deployment:** Pi setup scripts exist (`setup_pi.sh`), but primary dev is Mac.
