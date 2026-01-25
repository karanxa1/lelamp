import time
import sys
from lelamp.service.rgb.rgb_service import RGBService

def test_pattern():
    print("Initializing RGB Service on /dev/serial0...")
    service = RGBService(port='/dev/serial0')
    
    if not service.ser:
        print("Failed to initialize serial port. Check connections and permissions.")
        return

    service.start()
    time.sleep(1) # Allow thread to start

    print("Sending SOLID RED...")
    service.dispatch("solid", (255, 0, 0))
    time.sleep(1)
    
    print("Sending SOLID GREEN...")
    service.dispatch("solid", (0, 255, 0))
    time.sleep(1)
    
    print("Sending SOLID BLUE...")
    service.dispatch("solid", (0, 0, 255))
    time.sleep(1)

    print("Sending PAINT pattern (gradient)...")
    colors = []
    for i in range(64):
        # Create a simple generic gradient
        r = (i * 4) % 255
        g = (i * 8) % 255
        b = (255 - i * 4) % 255
        colors.append((r, g, b))
    
    service.dispatch("paint", colors)
    time.sleep(2)
    
    print("Clearing...")
    service.clear()
    service.stop()
    print("Test complete.")

if __name__ == "__main__":
    try:
        test_pattern()
    except KeyboardInterrupt:
        print("\nInterrupted.")
