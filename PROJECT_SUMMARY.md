# 🪔 LeLamp Nova - Technical Code Summary

## 1. Core Logic: `main.py`
The `LeLampAgent` class is the central orchestrator. It runs an event loop that manages:
*   **Audio Pipeline:**
    *   **Input:** Captures microphone audio using `sounddevice` at **16kHz**.
    *   **STT (Ear):** Streams audio chunks to **Deepgram (Nova-2 model)** via WebSocket.
    *   **VAD:** Deepgram handles Voice Activity Detection. When speech ends (endpointing: 300ms), it returns a transcript.
    *   **LLM (Brain):** Sends transcript + context to **OpenAI GPT-4o-mini**.
    *   **TTS (Voice):** Converts LLM text to speech using `edge_tts` (ultra-low latency).
    *   **Output:** Plays audio via `sounddevice` at 24kHz.

*   **Tool Calling System:**
    *   The LLM can execute Python functions. `_execute_tool_calls` handles:
        *   `set_led_color`: Changes LED strip.
        *   `play_animation`: Triggers motor sequences (e.g., "excited").
        *   `start_hand_tracking`: Enables Vision Service.

## 2. Motor Control: `direct_motors_service.py`
Controls the 5-DOF robotic arm using Feetech STS3215 Serial Bus Servos.
*   **Direct Serial Protocol:** Bypasses external libraries for raw speed. Sends hex packets (Header `FF FF`, ID, Length, Instruction `WRITE`, Calc Checksum).
*   **Animation Engine:**
    *   **Recordings:** Reads `.csv` files (time, motor1_pos, motor2_pos...).
    *   **Relative Playback:** Animations are relative to current position or Home, allowing smooth blending.
    *   **Idle Thread:** A background thread adds subtle "breathing" movements (sine wave on wrist/base) when no specific animation is playing, making the lamp feel alive.

## 3. Vision System: `vision_service.py`
Uses MediaPipe Hand Tracking (TFLite) to control the lamp.
*   **Tracking Loop:** Runs in a separate thread to not block the main app.
*   **Hand Detection:** Identifies 21 hand landmarks. 
    *   **Target:** Tracks Index Finger Tip (Landmark 8).
    *   **Mapping:** Maps X/Y screen coordinates to Yaw/Pitch motor angles.
    *   **Inversion:** Axies are inverted so the lamp moves *with* your hand (Mirror effect).
    *   **Smoothing:** Applies exponential smoothing (`alpha=0.2`) to remove jitter.
*   **Gesture Recognition:**
    *   **Fist:** Detected if finger tips are below knuckles. Sets `locked = True` (Pauses tracking).
    *   **Open Hand:** Sets `locked = False` (Resumes tracking).
*   **Integration:** When active, it overrides the Motor Service's idle animation.

## 4. Hardware Services
*   **RGB Service (`rgb_service.py`):** Controls WS2812B LEDs via `rpi_ws281x`. Uses DMA channel 10 to avoid conflicting with audio PWM.
*   **Alarm Service:** runs a background check every minute to trigger wake-up events.

## 5. Deployment
*   **Mac:** Runs full stack (Vision enabled).
*   **Pi:** Runs headless. Vision is optional/disabled if camera not present. 
*   **Startup:** `start.sh` handles virtual environment activation and port discovery.
