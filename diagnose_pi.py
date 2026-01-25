"""
Diagnostic Script for LeLamp on Raspberry Pi
Checks: MediaPipe, Camera, Audio
"""
import sys
import time
import os

print("\n🔍 LeLamp Diagnostic Tool")
print("================================")
print(f"Python Version: {sys.version.split()[0]}")

# 1. Check MediaPipe
print("\n[1/3] Checking MediaPipe...")
try:
    import mediapipe as mp
    print(f"✅ MediaPipe imported successfully")
except ImportError as e:
    print(f"❌ MediaPipe Import Failed: {e}")
    try:
        import mediapipe_rpi4
        print(f"⚠️ Found 'mediapipe_rpi4' but standard import failed.")
    except ImportError:
        print("❌ 'mediapipe_rpi4' also not found.")

# 2. Check Camera
print("\n[2/3] Checking Camera (OpenCV)...")
try:
    import cv2
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ ERROR: Could not open /dev/video0")
    else:
        # Try to read a frame
        ret, frame = cap.read()
        if ret:
            h, w = frame.shape[:2]
            print(f"✅ Camera Working! Resolution: {w}x{h}")
            
            # Try to utilize MediaPipe on this frame
            if 'mp' in locals():
                mp_hands = mp.solutions.hands
                with mp_hands.Hands(static_image_mode=True, max_num_hands=1) as hands:
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = hands.process(rgb)
                    if results.multi_hand_landmarks:
                        print("🎉 HAND DETECTED in single frame test!")
                    else:
                        print("ℹ️ No hand detected in test frame (expected)")
        else:
            print("❌ Camera opened, but failed to read frame.")
        cap.release()
except Exception as e:
    print(f"❌ Camera Error: {e}")

# 3. Check Audio
print("\n[3/3] Checking Audio...")
try:
    import sounddevice as sd
    devs = sd.query_devices()
    print(f"✅ Found {len(devs)} audio devices")
    
    # Check for Input
    try:
        sd.check_input_settings(device=None, channels=1, dtype='int16', samplerate=44100)
        print("✅ Input: 44100Hz Supported")
    except Exception as e:
        print(f"⚠️ Input 44100Hz Issue: {e}")
        try:
            sd.check_input_settings(device=None, channels=1, dtype='int16', samplerate=48000)
            print("✅ Input: 48000Hz Supported")
        except:
            print("❌ Input: Neither 44100Hz nor 48000Hz verified.")

except Exception as e:
    print(f"❌ Audio Error: {e}")

print("\nDone.")
