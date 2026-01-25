
import mediapipe as mp
print(f"MediaPipe version: {mp.__version__}")
try:
    # Try standard way first (might fail)
    try:
        print(f"Solutions: {dir(mp.solutions)}")
    except AttributeError:
        print("Standard mp.solutions access failed.")

    # Try explicit import
    from mediapipe.python.solutions import hands
    print(f"Explicit import success: {hands}")
    
    # Verify usage
    mp_hands = hands
    print("Workaround verified.")

except Exception as e:
    print(f"Error: {e}")
