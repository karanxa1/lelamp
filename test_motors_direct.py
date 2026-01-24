"""
Direct motor test script - bypasses lerobot checks
Tests Feetech STS3215 servos directly via serial
"""
import serial
import time
import struct

PORT = '/dev/cu.usbmodem5AE60864421'  # Auto-detected on Mac
BAUDRATE = 1000000

# STS3215 Protocol constants
INST_PING = 0x01
INST_READ = 0x02
INST_WRITE = 0x03
INST_REG_WRITE = 0x04
INST_ACTION = 0x05
INST_SYNC_WRITE = 0x83

# Register addresses for STS3215
ADDR_TORQUE_ENABLE = 40
ADDR_GOAL_POSITION = 42
ADDR_PRESENT_POSITION = 56


def build_packet(motor_id: int, instruction: int, params: bytes = b'') -> bytes:
    """Build a Feetech protocol packet"""
    length = len(params) + 2
    packet = bytes([0xFF, 0xFF, motor_id, length, instruction]) + params
    checksum = (~(motor_id + length + instruction + sum(params))) & 0xFF
    return packet + bytes([checksum])


def read_position(ser: serial.Serial, motor_id: int) -> int:
    """Read current position from motor"""
    packet = build_packet(motor_id, INST_READ, bytes([ADDR_PRESENT_POSITION, 2]))
    ser.write(packet)
    time.sleep(0.01)
    response = ser.read(20)
    if len(response) >= 7:
        # Position is 2 bytes, little-endian
        pos = response[5] | (response[6] << 8)
        return pos
    return -1


def set_torque(ser: serial.Serial, motor_id: int, enable: bool):
    """Enable/disable motor torque"""
    packet = build_packet(motor_id, INST_WRITE, bytes([ADDR_TORQUE_ENABLE, 1 if enable else 0]))
    ser.write(packet)
    time.sleep(0.01)
    ser.read(20)  # Clear response


def set_position(ser: serial.Serial, motor_id: int, position: int):
    """Set goal position (0-4095, center is ~2048)"""
    pos_low = position & 0xFF
    pos_high = (position >> 8) & 0xFF
    packet = build_packet(motor_id, INST_WRITE, bytes([ADDR_GOAL_POSITION, pos_low, pos_high]))
    ser.write(packet)
    time.sleep(0.01)
    ser.read(20)  # Clear response


def main():
    print(f"Opening port: {PORT}")
    ser = serial.Serial(PORT, BAUDRATE, timeout=0.5)
    time.sleep(0.5)
    
    motor_names = {1: 'base_yaw', 2: 'base_pitch', 3: 'elbow_pitch', 4: 'wrist_roll', 5: 'wrist_pitch'}
    
    # Read current positions
    print("\n=== Reading Motor Positions ===")
    for motor_id in range(1, 6):
        pos = read_position(ser, motor_id)
        print(f"Motor {motor_id} ({motor_names[motor_id]}): position = {pos}")
    
    # Enable torque on all motors
    print("\n=== Enabling Torque ===")
    for motor_id in range(1, 6):
        set_torque(ser, motor_id, True)
        print(f"Motor {motor_id}: torque enabled")
    
    # Small test movement - move motor 1 (base_yaw) slightly
    print("\n=== Test Movement ===")
    input("Press Enter to move motor 1 (base_yaw) to center position (2048)...")
    set_position(ser, 1, 2048)
    print("Motor 1 moved to center!")
    time.sleep(1)
    
    # Read final positions
    print("\n=== Final Positions ===")
    for motor_id in range(1, 6):
        pos = read_position(ser, motor_id)
        print(f"Motor {motor_id}: position = {pos}")
    
    # Disable torque
    print("\n=== Disabling Torque ===")
    for motor_id in range(1, 6):
        set_torque(ser, motor_id, False)
    print("All motors torque disabled")
    
    ser.close()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    main()
