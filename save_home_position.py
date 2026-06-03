"""Read current motor positions and save as new home offsets.

Pose the lamp by hand to the position you want it to assume at boot, then run
this script. Motor 3 (elbow_pitch) was physically removed — only 4 motors
(IDs 1, 2, 4, 5) are read.

Make sure the main agent is NOT running, or the serial port will be busy.
"""
import serial, time, glob, json, sys

PORT = (glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/ttyACM*') + [None])[0]
if not PORT:
    print("No port found! Stop the agent and check USB connection."); sys.exit(1)

# Motor IDs and names — elbow_pitch (ID 3) removed.
MOTORS = [
    (1, "base_yaw"),
    (2, "base_pitch"),
    (4, "wrist_roll"),
    (5, "wrist_pitch"),
]

print(f"Port: {PORT}")
try:
    ser = serial.Serial(PORT, 1000000, timeout=0.5)
except serial.SerialException as e:
    print(f"Could not open {PORT}: {e}")
    print("Is the agent (main.py) still running? Stop it first.")
    sys.exit(1)
time.sleep(0.2)


def _build(mid, inst, params):
    """Build a Feetech protocol packet."""
    length = len(params) + 2
    pkt = bytes([0xFF, 0xFF, mid, length, inst]) + params
    return pkt + bytes([(~(mid + length + inst + sum(params))) & 0xFF])


def set_torque(mid, enable):
    ser.write(_build(mid, 0x03, bytes([40, 1 if enable else 0])))
    time.sleep(0.005)
    ser.read(20)


def read_pos(mid):
    ser.write(_build(mid, 0x02, bytes([56, 2])))
    time.sleep(0.01)
    resp = ser.read(20)
    if len(resp) >= 7:
        return resp[5] | (resp[6] << 8)
    return None


# Disable torque so any small drift from "where the user posed it" doesn't
# get corrected away before we read. Then read present position.
print("\nDisabling torque so the lamp stays where you posed it...")
for mid, _ in MOTORS:
    set_torque(mid, False)

print("Reading current positions...")
offsets = {}
for mid, name in MOTORS:
    pos = read_pos(mid)
    if pos is not None:
        offsets[name] = pos
        print(f"  Motor {mid} ({name}): {pos}")
    else:
        print(f"  Motor {mid} ({name}): READ FAILED — skipped")

ser.close()

if len(offsets) != len(MOTORS):
    print(f"\n⚠️  Only {len(offsets)}/{len(MOTORS)} motors responded. NOT saving.")
    print("Check power, wiring, and that the agent isn't running.")
    sys.exit(1)

with open("motor_offsets.json", "w") as f:
    json.dump(offsets, f, indent=2)

print(f"\n✓ Saved to motor_offsets.json:")
print(json.dumps(offsets, indent=2))
print("\nNext time the agent starts, this is the position it will go to.")
