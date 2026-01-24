"""Fast Motor Homing - Moves all motors to home position from motor_offsets.json"""
import serial, time, glob, json

PORT = (glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/ttyACM*') + [None])[0]
if not PORT:
    print("No port!"); exit(1)

# Load offsets
with open("motor_offsets.json", "r") as f:
    offsets = json.load(f)

# Motor ID to offset name mapping
motor_map = {1: "base_yaw", 2: "base_pitch", 3: "elbow_pitch", 4: "wrist_roll", 5: "wrist_pitch"}

print(f"Port: {PORT}")
ser = serial.Serial(PORT, 1000000, timeout=0.5)
time.sleep(0.2)

def cmd(mid, inst, params):
    pkt = bytes([0xFF, 0xFF, mid, len(params)+2, inst]) + params
    pkt += bytes([(~(mid + len(params)+2 + inst + sum(params))) & 0xFF])
    ser.write(pkt); time.sleep(0.003); ser.read(20)

# Enable torque and move ALL motors to home positions
print("Moving to home position...")
for mid in range(1, 6):
    pos = offsets.get(motor_map[mid], 2048)
    cmd(mid, 0x03, bytes([40, 1]))  # Torque ON
    cmd(mid, 0x03, bytes([42, pos & 0xFF, (pos >> 8) & 0xFF]))  # Position
    print(f"  Motor {mid} ({motor_map[mid]}): {pos}")

print("Motors at HOME position!")
ser.close()
print("Done!")

