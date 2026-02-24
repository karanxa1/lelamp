"""
RGB LED Service using SN74AHCT125N Level Shifter + rpi_ws281x
Controls WS2812B 8x8 LED matrix directly via Raspberry Pi GPIO18
"""

from typing import Any, List, Union, Tuple
import time
import sys
from ..base import ServiceBase

# GPIO control via rpi_ws281x (Raspberry Pi only)
LED_AVAILABLE = False
try:
    from rpi_ws281x import PixelStrip, Color
    LED_AVAILABLE = True
except ImportError:
    pass


class RGBService(ServiceBase):
    """
    Controls WS2812B 8x8 LED matrix via SN74AHCT125N level shifter.
    
    Wiring:
    - Pi GPIO18 (Pin 12) → SN74AHCT125N 1A (Pin 2)
    - SN74AHCT125N 1Y (Pin 3) → LED DIN
    - SN74AHCT125N 1OE (Pin 1) → GND (enable)
    - SN74AHCT125N VCC (Pin 14) → 5V
    - SN74AHCT125N GND (Pin 7) → Common GND
    """
    
    # GPIO18 (PWM0) is the standard pin for WS281x LEDs
    LED_PIN = 18
    LED_FREQ_HZ = 800000
    LED_DMA = 10
    LED_CHANNEL = 0
    
    def __init__(self, 
                 led_count: int = 64,
                 port: str = None,  # Kept for backward compatibility, ignored
                 baud_rate: int = None,  # Ignored
                 led_dma: int = 10,
                 led_brightness: int = 32,
                 led_invert: bool = False):
        super().__init__("rgb")
        
        self.led_count = led_count
        self.led_brightness = max(0, min(255, led_brightness))
        self.led_invert = led_invert
        self.strip = None
        
        if not LED_AVAILABLE:
            self.logger.warning("rpi_ws281x not available (Mac mode or missing library)")
            return
            
        try:
            self.strip = PixelStrip(
                self.led_count,
                self.LED_PIN,
                self.LED_FREQ_HZ,
                led_dma,
                led_invert,
                self.led_brightness,
                self.LED_CHANNEL
            )
            self.strip.begin()
            self.logger.info(f"LED strip initialized: {led_count} LEDs on GPIO{self.LED_PIN}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LED strip: {e}")
            self.strip = None

    def handle_event(self, event_type: str, payload: Any):
        if not self.strip:
            self.logger.warning("LED strip not available, skipping event")
            return

        if event_type == "solid":
            self._handle_solid(payload)
        elif event_type == "paint":
            self._handle_paint(payload)
        else:
            self.logger.warning(f"Unknown event type: {event_type}")

    def _parse_color(self, color_code: Union[int, tuple]) -> Tuple[int, int, int]:
        """Convert color input to (r, g, b) tuple"""
        if isinstance(color_code, tuple) and len(color_code) == 3:
            return (color_code[0], color_code[1], color_code[2])
        elif isinstance(color_code, int):
            r = (color_code >> 16) & 0xFF
            g = (color_code >> 8) & 0xFF
            b = color_code & 0xFF
            return (r, g, b)
        else:
            self.logger.error(f"Invalid color format: {color_code}")
            return (0, 0, 0)

    def _handle_solid(self, color_code: Union[int, tuple]):
        """Fill entire strip with single color"""
        r, g, b = self._parse_color(color_code)
        color = Color(r, g, b)
        
        for i in range(self.led_count):
            self.strip.setPixelColor(i, color)
        self.strip.show()
        self.logger.debug(f"Solid color set: RGB({r},{g},{b})")

    def _handle_paint(self, colors: List[Union[int, tuple]]):
        """Set individual pixel colors"""
        if not isinstance(colors, list):
            self.logger.error(f"Paint payload must be a list, got: {type(colors)}")
            return
        
        for i in range(self.led_count):
            if i < len(colors):
                r, g, b = self._parse_color(colors[i])
            else:
                r, g, b = 0, 0, 0
            self.strip.setPixelColor(i, Color(r, g, b))
        
        self.strip.show()
        self.logger.debug(f"Paint: {min(len(colors), self.led_count)} pixels")

    def set_brightness(self, brightness: int):
        """Set LED brightness (0-255)"""
        if self.strip:
            self.led_brightness = max(0, min(255, brightness))
            self.strip.setBrightness(self.led_brightness)
            self.strip.show()
    
    def clear(self):
        """Turn off all LEDs"""
        if self.strip:
            for i in range(self.led_count):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
    
    def stop(self, timeout: float = 5.0):
        """Cleanup and stop service"""
        self.clear()
        super().stop(timeout)