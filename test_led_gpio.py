#!/usr/bin/env python3
"""
Test script for 8x8 WS2812B LED matrix via SN74AHCT125N level shifter.

Wiring:
  Pi GPIO18 (Pin 12) → SN74AHCT125N 1A (Pin 2)
  SN74AHCT125N 1Y (Pin 3) → LED DIN
  SN74AHCT125N 1OE (Pin 1) → GND
  SN74AHCT125N VCC (Pin 14) → 5V
  SN74AHCT125N GND (Pin 7) → Common GND
  
Run with: sudo python3 test_led_gpio.py
"""

import time

try:
    from rpi_ws281x import PixelStrip, Color
except ImportError:
    print("Error: rpi_ws281x not installed. Run: sudo pip3 install rpi_ws281x")
    exit(1)

LED_COUNT = 64
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 50
LED_INVERT = False
LED_CHANNEL = 0

def rainbow_cycle(strip, wait_ms=20, iterations=2):
    """Rainbow animation across all pixels."""
    for j in range(256 * iterations):
        for i in range(strip.numPixels()):
            pos = (i * 256 // strip.numPixels() + j) % 256
            if pos < 85:
                color = Color(pos * 3, 255 - pos * 3, 0)
            elif pos < 170:
                pos -= 85
                color = Color(255 - pos * 3, 0, pos * 3)
            else:
                pos -= 170
                color = Color(0, pos * 3, 255 - pos * 3)
            strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)

def main():
    print("Initializing LED strip on GPIO18...")
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    
    print("Testing RED...")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(255, 0, 0))
    strip.show()
    time.sleep(1)
    
    print("Testing GREEN...")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 255, 0))
    strip.show()
    time.sleep(1)
    
    print("Testing BLUE...")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 255))
    strip.show()
    time.sleep(1)
    
    print("Rainbow animation...")
    rainbow_cycle(strip)
    
    print("Clearing LEDs...")
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    
    print("Done!")

if __name__ == "__main__":
    main()
