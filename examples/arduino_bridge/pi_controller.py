import serial
import serial.tools.list_ports
import time
import sys

# Configuration
# Option 1: USB Connection (Recommended for beginners)
SERIAL_PORT = '/dev/ttyACM0' 
# Option 2: GPIO/UART Pins (GPIO 14 TX -> Arduino RX)
# SERIAL_PORT = '/dev/serial0' 

BAUD_RATE = 115200

def list_available_ports():
    ports = serial.tools.list_ports.comports()
    print("\nAvailable Ports:")
    for port in ports:
        print(f" - {port.device} ({port.description})")
    print("")

def main():
    try:
        # Initialize Serial Connection
        print(f"Connecting to Arduino on {SERIAL_PORT}...")
        arduino = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for Arduino to reset
        print("Connected!")

        # Example: Cycle through colors
        colors = [
            (255, 0, 0),   # Red
            (0, 255, 0),   # Green
            (0, 0, 255),   # Blue
            (255, 255, 0), # Yellow
            (0, 255, 255), # Cyan
            (255, 0, 255), # Magenta
            (255, 255, 255), # White
            (0, 0, 0)      # Off
        ]

        while True:
            for r, g, b in colors:
                print(f"Sending Color: R={r}, G={g}, B={b}")
                send_color(arduino, r, g, b)
                time.sleep(1)

    except serial.SerialException as e:
        print(f"\n[Error] Could not connect to {SERIAL_PORT}")
        print(f"Details: {e}")
        list_available_ports()
        print("Tip: Update 'SERIAL_PORT' in this script to one of the ports listed above.")
    except KeyboardInterrupt:
        print("\nExiting...")
        if 'arduino' in locals() and arduino.is_open:
            arduino.close()

def send_color(ser, r, g, b):
    # Packet Structure: 's' + R + G + B
    # 's' is the command char defined in Arduino code
    packet = bytearray([ord('s'), r, g, b])
    ser.write(packet)

if __name__ == "__main__":
    main()
