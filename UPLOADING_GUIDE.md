# How to Upload Code to Arduino

You cannot update the Arduino code just by running `git pull` on the Raspberry Pi. You must "Flash" (upload) the new code to the Arduino board itself using a USB cable.

## Prerequisites
1.  **Arduino IDE**: Installed on your Computer (Mac/Windows) or the Raspberry Pi. [Download Here](https://www.arduino.cc/en/software).
2.  **USB Cable**: A cable to connect the Arduino to your Computer/Pi.
3.  **Disconnect Main Wires**: **CRITICAL!** You MUST unplug the **Rx** and **Tx** wires connected to the Raspberry Pi before uploading.
    *   *Why?* The USB connection uses the same lines as the Rx/Tx pins. If they are connected to the Pi, the upload will fail (or get stuck on "Uploading...").

## Steps using Arduino IDE

1.  **Open Code**:
    *   Launch **Arduino IDE**.
    *   Open the file `arduino/main/main.ino` from this repository.
    *   (Or verify you have the latest code: It should have `void rainbowCycle` in it).

2.  **Install Library**:
    *   Go to **Tools** -> **Manage Libraries...**
    *   Search for **"Adafruit NeoPixel"**.
    *   Click **Install** (Install all dependencies if asked).

3.  **Select Board & Port**:
    *   Connect Arduino via USB.
    *   Go to **Tools** -> **Board** -> Select your Arduino (e.g., "Arduino Uno").
    *   Go to **Tools** -> **Port** -> Select the USB port (e.g., `/dev/cu.usbmodem...` on Mac or `COM3` on Windows).

4.  **Upload**:
    *   Click the **Right Arrow (⮕)** button (Upload).
    *   Wait for **"Done uploading"** message at the bottom.

5.  **Verify**:
    *   Once uploaded, the Arduino should immediately start the **Rainbow Cycle** animation on the LED Matrix (if powered).

6.  **Reconnect**:
    *   Unplug USB (optional, or keep for power).
    *   **Reconnect the Rx/Tx wires** to the Raspberry Pi.
    *   Reset Arduino.

## Method 2: Command Line on Raspberry Pi (Advanced)
If you don't want to unplug wires and move the Arduino to a computer, you can install `arduino-cli` on the Pi:

1.  **Install**:
    ```bash
    curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
    ```
2.  **Install Core**:
    ```bash
    bin/arduino-cli core install arduino:avr
    ```
3.  **Install Lib**:
    ```bash
    bin/arduino-cli lib install "Adafruit NeoPixel"
    ```
4.  **Compile & Upload** (Rx MUST still be disconnected!):
    ```bash
    bin/arduino-cli compile --fqbn arduino:avr:uno arduino/main/main.ino
    bin/arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno arduino/main/main.ino
    ```
