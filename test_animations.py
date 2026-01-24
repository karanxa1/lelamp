"""Test all emotion animations"""
import time
import sys
sys.path.insert(0, '.')

from lelamp.service.motors.direct_motors_service import DirectMotorsService
import glob

# Find port
ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/ttyACM*')
if not ports:
    print("No motor port found!")
    exit(1)

PORT = ports[0]
print(f"Port: {PORT}")

# Initialize motor service
motors = DirectMotorsService(port=PORT, fps=30)
motors.start()

# All available animations
animations = ["curious", "excited", "happy_wiggle", "headshake", "nod", "sad", "scanning", "shock", "shy", "wake_up"]

print(f"\nTesting {len(animations)} animations...")
print("=" * 40)

for i, anim in enumerate(animations, 1):
    print(f"\n[{i}/{len(animations)}] Playing: {anim}")
    motors.dispatch("play", anim)
    
    # Wait for animation to complete (most are ~2-3 seconds)
    time.sleep(4)
    
    # Return to home briefly
    motors._handle_home()
    time.sleep(1)

print("\n" + "=" * 40)
print("All animations tested!")
motors.stop()
