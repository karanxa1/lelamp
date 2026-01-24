"""Read current motor positions and save as new home offsets"""
import serial, time, glob, json

PORT = (glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/ttyACM*') + [None])[0]
if not PORT:
    print("No port!"); exit(1)

print(f"Port: {PORT}")
ser = serial.Serial(PORT, 1000000, timeout=0.5)
time.sleep(0.2)

def read_pos(mid):
    # Read Present Position (Address 56, 2 bytes)
    pkt = bytes([0xFF, 0xFF, mid, 4, 0x02, 56, 2])
    checksum = (~(mid + 4 + 0x02 + 56 + 2)) & 0xFF
    pkt += bytes([checksum])
    ser.write(pkt)
    time.sleep(0.01)
    resp = ser.read(20)
    if len(resp) >= 7:
        pos = resp[5] | (resp[6] << 8)
        return pos
    return None

# Motor IDs: 1=base_yaw, 2=base_pitch, 3=elbow_pitch, 4=wrist_roll, 5=wrist_pitch
names = {1: "base_yaw", 2: "base_pitch", 3: "elbow_pitch", 4: "wrist_roll", 5: "wrist_pitch"}
offsets = {}

print("\nReading current positions...")
for mid in range(1, 6):
    pos = read_pos(mid)
    if pos is not None:
        offsets[names[mid]] = pos
        print(f"  Motor {mid} ({names[mid]}): {pos}")
    else:
        print(f"  Motor {mid}: READ FAILED")

ser.close()

# Save to file
with open("motor_offsets.json", "w") as f:
    json.dump(offsets, f, indent=2)
    
print(f"\nSaved to motor_offsets.json:")
print(json.dumps(offsets, indent=2))
