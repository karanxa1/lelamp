
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time
import os

# --- Real Motor Service ---
from lelamp.service.motors.direct_motors_service import DirectMotorsService
import glob

def run_vision_test():
    print("🎥 Starting Vision Test with REAL MOTORS (Task API)")
    print("Press ESC to quit")
    
    # 1. Connect Motors
    port = None
    ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbmodem*')
    if ports:
        port = ports[0]
        print(f"✅ Found motor port: {port}")
    else:
        print("❌ No motor port found! Using Mock.")
        
    motor = None
    if port:
        try:
            motor = DirectMotorsService(port=port)
            motor.start()
            print("✅ Motors connected and homing...")
            motor._handle_home()
            time.sleep(1)
        except Exception as e:
            print(f"❌ Motor connection failed: {e}")
            return

    if motor:
        # Stop idle animation while tracking
        motor._is_animating = True
        print("✅ Idle animation paused for tracking")

    # 2. Load Vision Model
    model_path = os.path.abspath("lelamp/service/vision/models/hand_landmarker.task")
    if not os.path.exists(model_path):
        print(f"❌ Model not found: {model_path}")
        return

    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(base_options=base_options, num_hands=1)
    detector = vision.HandLandmarker.create_from_options(options)

    cap = cv2.VideoCapture(0)
    print("✅ Model loaded. Starting camera...")

    # Smoothing
    smooth_yaw = 0.0
    smooth_pitch = 0.0
    alpha = 0.3
    
    # Tracking State
    is_locked = False
    
    def is_fist(landmarks):
        # Allow checking if fingers are curled - RELAXED THRESHOLD
        # Simple heuristic: Check if fingertips are close to wrist (landmark 0)
        wrist = landmarks[0]
        tips = [8, 12, 16, 20]
        
        curled_count = 0
        for tip_idx in tips:
            # Distance from tip to wrist
            tip = landmarks[tip_idx]
            dist = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)**0.5
            # Relaxed threshold to 0.25 (unit coordinates)
            if dist < 0.25: 
                curled_count += 1
                
        return curled_count >= 3 # At least 3 fingers curled = Fist

    try:
        while True:
            success, image = cap.read()
            if not success: 
                print("❌ Camera read failed")
                break
            
            image = cv2.flip(image, 1)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            
            detection_result = detector.detect(mp_image)
            
            tracker_status = "unlocked"
            status_color = (0, 255, 0) # Green
            
            if detection_result.hand_landmarks:
                for hand_landmarks in detection_result.hand_landmarks:
                    # Check gesture
                    if is_fist(hand_landmarks):
                        is_locked = True
                        tracker_status = "LOCKED (Fist)"
                        status_color = (0, 0, 255) # Red
                    else:
                        is_locked = False
                        tracker_status = "TRACKING (Open)"
                        status_color = (0, 255, 0) # Green

                    # Draw landmarks manually
                    h, w, _ = image.shape
                    for lm in hand_landmarks:
                        cx, cy = int(lm.x * w), int(lm.y * h)
                        cv2.circle(image, (cx, cy), 5, status_color, -1)
                    
                    if not is_locked:
                        # Logic: Index Finger Tip (Index 8)
                        idx_tip = hand_landmarks[8]
                        
                        # --- MAPPING LOGIC ---
                        # X Axis (0.0 Left -> 1.0 Right) -> Yaw: -60 to +60
                        raw_yaw = (idx_tip.x - 0.5) * 120
                        
                        # Y Axis (0.0 Top -> 1.0 Bottom) -> Pitch: +40 to -40
                        raw_pitch = (0.5 - idx_tip.y) * 80
                        
                        # Smoothing
                        smooth_yaw = (smooth_yaw * (1-alpha)) + (raw_yaw * alpha)
                        smooth_pitch = (smooth_pitch * (1-alpha)) + (raw_pitch * alpha)
                        
                        if motor:
                            # --- UPDATE MOTORS ---
                            # Base Yaw
                            yaw_offset = motor.offsets.get('base_yaw', 2048)
                            yaw_pos = int(yaw_offset + (smooth_yaw / 180.0) * 2048)
                            motor._set_position(1, yaw_pos)
                            
                            # Pitch (Up/Down) with Inverse Kinematics
                            k_base = -0.5
                            k_elbow = 0.8
                            k_wrist = -0.3
                            
                            # Base Pitch
                            bp_offset = motor.offsets.get('base_pitch', 2048)
                            bp_pos = int(bp_offset + (smooth_pitch * k_base / 180.0) * 2048)
                            motor._set_position(2, bp_pos)
                            
                            # Elbow Pitch
                            ep_offset = motor.offsets.get('elbow_pitch', 2048)
                            ep_pos = int(ep_offset + (smooth_pitch * k_elbow / 180.0) * 2048)
                            motor._set_position(3, ep_pos)
                            
                            # Wrist Pitch
                            wp_offset = motor.offsets.get('wrist_pitch', 2048)
                            wp_pos = int(wp_offset + (smooth_pitch * k_wrist / 180.0) * 2048)
                            motor._set_position(5, wp_pos)

                    print(f"\r🖐️ {tracker_status} | Target: Yaw={smooth_yaw:.1f}° Pitch={smooth_pitch:.1f}°   ", end="")

            cv2.putText(image, tracker_status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
            cv2.imshow("Vision Test (REAL MOTOR)", image)
            if cv2.waitKey(1) & 0xFF == 27:
                break
                
    except KeyboardInterrupt:
        pass
    finally:
        print("\nStopping...")
        if motor:
            motor._is_animating = False # Resume idle
            motor.stop()
        cap.release()
        cv2.destroyAllWindows()
        detector.close()

if __name__ == "__main__":
    run_vision_test()
