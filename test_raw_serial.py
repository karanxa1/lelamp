import serial
import time
import sys

# Try common ports
ports = ['/dev/serial0', '/dev/ttyACM0', '/dev/ttyUSB0', '/dev/ttyAMA0', '/dev/ttyS0']

def try_port(port_name):
    print(f"Attempting to open {port_name}...")
    try:
        ser = serial.Serial(port_name, 115200, timeout=1)
        # Toggle DTR to force reset on some Arduinos
        ser.dtr = False
        time.sleep(1)
        ser.dtr = True
        time.sleep(2) # Wait for bootloader
        
        print(f"Success! {port_name} is open.")
        
        # 1. Send Clear
        print("Sending CLEAR...")
        ser.write(b'c')
        time.sleep(0.5)
        
        # 2. Send Solid Red
        print("Sending RED...")
        ser.write(b's')
        ser.write(bytes([50, 0, 0]))  # Low brightness
        time.sleep(1)
        
        # 3. Send Solid Green
        print("Sending GREEN...")
        ser.write(b's')
        ser.write(bytes([0, 50, 0]))
        time.sleep(1)
        
        ser.close()
        print("Done.")
        return True
    except serial.SerialException as e:
        print(f"Failed {port_name}: {e}")
        return False

if __name__ == "__main__":
    success = False
    for port in ports:
        if try_port(port):
            success = True
            break
            
    if not success:
        print("\nCould not connect to any common serial port.")
        print("Please run 'ls /dev/tty*' to check available ports.")
