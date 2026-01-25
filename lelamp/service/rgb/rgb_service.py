from typing import Any, List, Union, Tuple
import serial
import time
from ..base import ServiceBase


class RGBService(ServiceBase):
    def __init__(self, 
                 led_count: int = 64,
                 port: str = '/dev/serial0',
                 baud_rate: int = 115200,
                 led_dma: int = 10,
                 led_brightness: int = 32,
                 led_invert: bool = False):
        super().__init__("rgb")
        
        self.led_count = led_count
        self.led_dma = led_dma
        self.led_brightness = led_brightness
        self.led_invert = led_invert
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=1)
            # Wait for Arduino reset
            time.sleep(2)
        except serial.SerialException as e:
            self.logger.error(f"Failed to open serial port {port}: {e}")
            self.ser = None

    def handle_event(self, event_type: str, payload: Any):
        if not self.ser or not self.ser.is_open:
            self.logger.warning("Serial port not open, skipping event")
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
            # Assumes 0xRRGGBB format
            r = (color_code >> 16) & 0xFF
            g = (color_code >> 8) & 0xFF
            b = color_code & 0xFF
            return (r, g, b)
        else:
            self.logger.error(f"Invalid color format: {color_code}")
            return (0, 0, 0)

    def _handle_solid(self, color_code: Union[int, tuple]):
        """Fill entire strip with single color via Serial"""
        r, g, b = self._parse_color(color_code)
        
        try:
            self.ser.write(b's')
            self.ser.write(bytes([r, g, b]))
            self.logger.debug(f"Sent solid color command: {r},{g},{b}")
        except Exception as e:
            self.logger.error(f"Error sending solid command: {e}")

    def _handle_paint(self, colors: List[Union[int, tuple]]):
        """Send pixel array via Serial"""
        if not isinstance(colors, list):
            self.logger.error(f"Paint payload must be a list, got: {type(colors)}")
            return
            
        data = bytearray()
        count = 0
        
        # Pad or truncate to match led_count exactly
        for i in range(self.led_count):
            if i < len(colors):
                r, g, b = self._parse_color(colors[i])
            else:
                r, g, b = 0, 0, 0 # Pad with black if list is short
            
            data.append(r)
            data.append(g)
            data.append(b)
            count += 1
            
        try:
            self.ser.write(b'p')
            self.ser.write(data)
            self.logger.debug(f"Sent paint command with {count} pixels")
        except Exception as e:
            self.logger.error(f"Error sending paint command: {e}")
    
    def clear(self):
        """Turn off all LEDs"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b'c')
            except Exception as e:
                self.logger.error(f"Error sending clear command: {e}")
    
    def stop(self, timeout: float = 5.0):
        """Close serial connection"""
        self.clear()
        if self.ser and self.ser.is_open:
            self.ser.close()
        super().stop(timeout)