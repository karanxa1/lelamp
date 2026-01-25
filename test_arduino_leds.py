
import time
import os
import sys
import glob

# Ensure we can import from lelamp
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lelamp.service.rgb.rgb_service import RGBService
from lelamp.service.rgb.led_faces import get_face

def find_arduino_port():
    """Helper to find Arduino Port"""
    # Prefer env var
    if os.getenv("RGB_PORT"):
        return os.getenv("RGB_PORT")
        
    if sys.platform == "darwin":
        ports = glob.glob('/dev/cu.usbmodem*')
        if not ports:
            print("❌ No /dev/cu.usbmodem* ports found!")
            return None
        # User might have multiple (Motors + LEDs)
        print(f"🔎 Found ports: {ports}")
        # Default to the LAST one if multiple, assuming most recently plugged in?
        # Or ask user. For test, we just pick one.
        return ports[-1] 
    else:
        # Raspberry Pi default
        return '/dev/ttyUSB0'

def main():
    port = find_arduino_port()
    if not port:
        print("⚠️ Could not find Arduino port. Set RGB_PORT or check connection.")
        return

    print(f"🔌 Connecting to Arduino at {port}...")
    rgb = RGBService(port=port)
    
    # Wait for Arduino reset
    print("⏳ Waiting for Arduino reset...")
    time.sleep(2)

    try:
        print("🔴 Testing SOLID RED (Text Protocol)")
        rgb.dispatch("solid", (255, 0, 0))
        time.sleep(1)

        print("🟢 Testing SOLID GREEN")
        rgb.dispatch("solid", (0, 255, 0))
        time.sleep(1)

        print("🔵 Testing SOLID BLUE")
        rgb.dispatch("solid", (0, 0, 255))
        time.sleep(1)
        
        print("😊 Testing HAPPY Face (Binary Protocol)")
        face = get_face("happy")
        rgb.dispatch("paint", face)
        time.sleep(2)
        
        print("😮 Testing SURPRISED Face")
        face = get_face("surprised")
        rgb.dispatch("paint", face)
        time.sleep(2)
        
        print("❤️ Testing HEART Face")
        face = get_face("heart")
        rgb.dispatch("paint", face)
        time.sleep(2)

        print("🧹 Clearing...")
        rgb.dispatch("solid", (0, 0, 0))
        time.sleep(0.5)
        
        print("✅ Test Complete!")
        
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        rgb.stop()

if __name__ == "__main__":
    main()
