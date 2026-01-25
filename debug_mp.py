
import mediapipe as mp
import os
import sys

print(f"Python: {sys.version}")
print(f"MediaPipe: {mp.__file__}")
print(f"Dir(mp): {dir(mp)}")

try:
    import mediapipe.python
    print("✅ import mediapipe.python success")
except ImportError as e:
    print(f"❌ import mediapipe.python failed: {e}")

try:
    from mediapipe.tasks import python
    print("✅ import mediapipe.tasks.python success")
except ImportError as e:
    print(f"❌ import mediapipe.tasks.python failed: {e}")
