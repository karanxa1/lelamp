import sounddevice as sd

def list_audio_devices():
    print("=== Available Audio Devices ===")
    print(sd.query_devices())
    print("\n=== Default Devices ===")
    try:
        print(f"Input: {sd.default.device[0]}")
        print(f"Output: {sd.default.device[1]}")
    except Exception as e:
        print(f"Error getting defaults: {e}")

if __name__ == "__main__":
    list_audio_devices()
