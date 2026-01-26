# Arduino & Raspberry Pi Setup Guide

This guide covers how to upload the code to your Arduino and how to connect it to the Raspberry Pi using **GPIO Data Pins** (UART) instead of USB.

## Part 1: Uploading Code to Arduino

You need to do this from your computer (Mac/PC) first.

1.  **Download Arduino IDE**: Install it from [arduino.cc](https://www.arduino.cc/en/software).
2.  **Open the Code**: Open the `arduino_bridge.ino` file you created.
3.  **Install Library**:
    *   Go to **Sketch** -> **Include Library** -> **Manage Libraries...**
    *   Search for **"Adafruit NeoPixel"**
    *   Click **Install**.
4.  **Connect Arduino**: Plug your Arduino into your computer via USB.
5.  **Select Board & Port**:
    *   Go to **Tools** -> **Board** -> Select your Arduino (e.g., "Arduino Uno").
    *   Go to **Tools** -> **Port** -> Select the USB port that appears.
6.  **Upload**: Click the arrow button (➡️) in the top left. Wait for "Done uploading."

---

## Part 2: Connecting via Data Pins (UART)

Yes, you can connect via pins! This uses the **UART** protocol.

### ⚠️ IMPORTANT VOLTAGE WARNING
*   **Raspberry Pi GPIO is 3.3V.**
*   **Arduino is 5V.**
*   **Safe Direction**: Pi sending to Arduino (3.3V -> 5V) is generally safe.
*   **Unsafe Direction**: Arduino sending to Pi (5V -> 3.3V) **WILL DAMAGE** your Pi without a level shifter.
*   **Since we are only sending commands TO the Arduino to control LEDs, direct connection for TX->RX is usually fine.**

### Wiring Diagram

| Raspberry Pi Pin | Connection | Arduino Pin |
| :--- | :---: | :--- |
| **GPIO 14 (TX)** | ➡️ | **RX (Pin 0)** |
| **GND (Ground)** | 🔗 | **GND** |
| **5V / Power** | ⚡ | **5V / VIN** |

1.  **Connect Grounds**: You MUST connect a GND pin from Pi to a GND pin on Arduino.
2.  **Connect Data**: Connect Pi **GPIO 14 (TXD)** to Arduino **RX (Pin 0)**.

*> **Note:** When uploading code to the Arduino later, you must **disconnect** the wire from Pin 0 (RX), or the upload will fail.*

---

## Part 3: Raspberry Pi Configuration

By default, the Pi uses its serial pins for the system console. You need to disable the console to use them for your code.

1.  **Open Config**: Run `sudo raspi-config`
2.  **Interface Options**: Select **Interface Options** -> **Serial Port**.
    *   "Would you like a login shell to be accessible over serial?" -> **No**
    *   "Would you like the serial port hardware to be enabled?" -> **Yes**
3.  **Reboot**: Exit and reboot your Pi (`sudo reboot`).

## Part 4: Updating the Python Script

When using GPIO pins, the port name changes.

**File:** `examples/arduino_bridge/pi_controller.py`

Change `SERIAL_PORT` to:
```python
# For Raspberry Pi 3/4/5 using GPIO pins:
SERIAL_PORT = '/dev/serial0' 
```

You can now run the script:
```bash
python3 examples/arduino_bridge/pi_controller.py
```
