# LED Matrix & Arduino Troubleshooting Guide

If your LEDs are not responding, follow these steps in order.

## Step 1: Verify Wiring & Power (Crucial!)

Most issues are due to power or wiring.

### 1. Power Supply
*   **The Problem**: 64 LEDs (8x8 matrix) at full white can draw ~3.8 Amps! The Arduino 5V pin CANNOT provide this.
*   **The Solution**: You likely need an **external 5V power supply** (2A minimum recommended for typical usage, 4A for full white).
*   **Wiring**:
    *   **External 5V (+) -> LED 5V**
    *   **External GND (-) -> LED GND**
    *   **External GND (-) -> Arduino GND** (Common Ground is MANDATORY!)

### 2. Signal Connection
*   **Arduino Pin 3** -> **LED DIN** (Data In)
*   **Arduino GND** -> **LED GND**

### Diagram
```
[External 5V Power]
      + (5V) ---------------------> [LED Matrix 5V]
      - (GND) --+-----------------> [LED Matrix GND]
                |
[Arduino]       |
      GND ------+
      Pin 3 ----------------------> [LED Matrix DIN]
      
[Raspberry Pi] (If using USB)
      USB Cable ------------------> [Arduino USB]
```

---

## Step 2: Test Arduino Independently

Rule out the Raspberry Pi first. Let's make sure the Arduino can light up the LEDs on its own.

1.  Open Arduino IDE.
2.  Use this simple "Test Sketch":
    ```cpp
    #include <Adafruit_NeoPixel.h>
    #define PIN 3
    #define NUMPIXELS 64
    Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

    void setup() {
      pixels.begin();
      pixels.setBrightness(50);
    }

    void loop() {
      // Blink Red
      for(int i=0; i<NUMPIXELS; i++) pixels.setPixelColor(i, pixels.Color(255, 0, 0));
      pixels.show();
      delay(500);

      // Blink Green
      for(int i=0; i<NUMPIXELS; i++) pixels.setPixelColor(i, pixels.Color(0, 255, 0));
      pixels.show();
      delay(500);
    }
    ```
3.  Upload this to your Arduino.
    *   **If LEDs light up:** Your wiring and power are good! The issue is the Pi connection.
    *   **If LEDs DO NOT light up:** The issue is hardware (Power, Wiring, or the LED strip itself). **Stop here and fix hardware.**

---

## Step 3: Verify Pi -> Arduino Connection

If Step 2 worked, now connect the Pi.

1.  Upload the **original `arduino_bridge.ino`** back to the Arduino (the one that waits for serial commands).
2.  Connect Arduino to Pi via USB.
3.  Check if Pi sees the Arduino:
    ```bash
    ls /dev/ttyACM*
    # OR
    ls /dev/ttyUSB*
    ```
    *Note the device name (e.g., `/dev/ttyACM0`).*

4.  Run the Python controller script manually:
    ```bash
    uv run examples/arduino_bridge/pi_controller.py
    ```
    *   **Edit the script** if your port is different (e.g., change `ttyACM0` to `ttyUSB0`).
    *   If this works, the LEDs should cycle colors.

---

## Step 4: Configure `main.py`

If Step 3 worked, update your main agent code.

1.  Open `main.py`.
2.  Look for `RGBService` initialization (around line 290).
3.  Ensure `port` matches what worked in Step 3.
    ```python
    self.rgb_service = RGBService(
        led_count=64, 
        port='/dev/ttyACM0',  # <--- MAKE SURE THIS IS CORRECT
        led_brightness=32
    )
    ```
