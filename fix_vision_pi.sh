#!/bin/bash
# Quick fix for vision service on Raspberry Pi
# Run this on the Pi: bash fix_vision_pi.sh

cd ~/techspark/lelamp

echo "🔧 Fixing vision service for mediapipe-rpi4..."

# Backup original
cp lelamp/service/vision/vision_service.py lelamp/service/vision/vision_service.py.backup

# Apply fix using sed
sed -i '18,31s/.*/        # MediaPipe Setup (TFLite Backend)\n        try:\n            self.mp_hands = mp.solutions.hands\n            self.hands = self.mp_hands.Hands(\n                static_image_mode=False,\n                max_num_hands=1,\n                min_detection_confidence=0.5,\n                min_tracking_confidence=0.5\n            )\n        except (AttributeError, ModuleNotFoundError):\n            # Fallback for mediapipe-rpi4\n            try:\n                import mediapipe_rpi4 as mp_rpi\n                self.mp_hands = mp_rpi.solutions.hands\n                self.hands = self.mp_hands.Hands(\n                    static_image_mode=False,\n                    max_num_hands=1,\n                    min_detection_confidence=0.5,\n                    min_tracking_confidence=0.5\n                )\n            except Exception as e:\n                logger.error(f"Failed to initialize MediaPipe: {e}")\n                raise/' lelamp/service/vision/vision_service.py

echo "✅ Vision service patched!"
echo ""
echo "Installing pyserial..."
.venv/bin/pip install pyserial>=3.5

echo ""
echo "✅ All fixes applied! Now run: ./start.sh"
