"""Fast Motor Homing - Instantly moves all motors to 0° and locks them"""
import serial, time, glob

PORT = (glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*') + [None])[0]
if not PORT:
    print("❌ No port!"); exit(1)

print(f"🔌 {PORT}")
ser = serial.Serial(PORT, 1000000, timeout=0.5)
time.sleep(0.2)

def cmd(mid, inst, params):
    pkt = bytes([0xFF, 0xFF, mid, len(params)+2, inst]) + params
    pkt += bytes([(~(mid + len(params)+2 + inst + sum(params))) & 0xFF])
    ser.write(pkt); time.sleep(0.003); ser.read(20)

# Enable torque and move ALL motors to center (2048 = 0°) FAST
print("⚡ Enabling torque & moving to 0°...")
for mid in range(1, 6):
    cmd(mid, 0x03, bytes([40, 1]))  # Torque ON
    cmd(mid, 0x03, bytes([42, 0x00, 0x08]))  # Position 2048 (0x0800)

print("🔒 Motors LOCKED at 0° position!")
print("   Torque is ON - motors will hold position")
ser.close()
print("✅ Done!")
