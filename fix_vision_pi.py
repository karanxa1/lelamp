#!/usr/bin/env python3
"""Quick fix for vision service on Raspberry Pi with mediapipe-rpi4"""

import os
import shutil

# Path to vision service
vision_file = os.path.expanduser("~/techspark/lelamp/lelamp/service/vision/vision_service.py")

print("🔧 Fixing vision service for mediapipe-rpi4...")

# Backup original
backup_file = vision_file + ".backup"
shutil.copy2(vision_file, backup_file)
print(f"✓ Backup created: {backup_file}")

# Read the file
with open(vision_file, 'r') as f:
    lines = f.readlines()

# Find and replace the MediaPipe initialization section (lines 18-31)
new_init = """        # MediaPipe Setup (TFLite Backend)
        try:
            self.mp_hands = mp.solutions.hands
            self.hands = self.mp_hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5
            )
        except (AttributeError, ModuleNotFoundError):
            # Fallback for mediapipe-rpi4
            try:
                import mediapipe_rpi4 as mp_rpi
                self.mp_hands = mp_rpi.solutions.hands
                self.hands = self.mp_hands.Hands(
                    static_image_mode=False,
                    max_num_hands=1,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
            except Exception as e:
                logger.error(f"Failed to initialize MediaPipe: {e}")
                raise
        
"""

# Replace lines 17-31 (0-indexed: 17-30)
new_lines = lines[:17] + [new_init] + lines[31:]

# Write back
with open(vision_file, 'w') as f:
    f.writelines(new_lines)

print("✅ Vision service patched!")
print("\nNow run:")
print("  .venv/bin/pip install pyserial>=3.5")
print("  ./start.sh")
