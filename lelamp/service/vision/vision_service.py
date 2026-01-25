"""Vision Service - MediaPipe TFLite Hand Tracking"""

import cv2
import time
import threading
import logging

# Try standard mediapipe first (works with both regular and mediapipe-rpi4)
try:
    import mediapipe as mp
except ImportError:
    mp = None

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self, motor_service=None, camera_index=0):
        if mp is None:
            raise ImportError("MediaPipe not available")
            
        self.motor_service = motor_service
        self.camera_index = camera_index
        self.running = False
        self.thread = None
        
        # MediaPipe Setup (TFLite Backend)
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Tracking State
        self.smooth_yaw = 0.0
        self.smooth_pitch = 0.0
        self.alpha = 0.2  # Smooth factor
        self.locked = False
        
    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        if self.motor_service:
            self.motor_service._is_animating = True
        logger.info("Vision Service started (MediaPipe Hand Tracking)")
        
    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1.0)
        if self.motor_service:
            self.motor_service._is_animating = False
        logger.info("Vision Service stopped")
        
    def _tracking_loop(self):
        # Retry logic for camera connection
        cap = None
        for i in range(5):
             cap = cv2.VideoCapture(self.camera_index)
             if cap.isOpened():
                 break
             time.sleep(1)
             
        if not cap or not cap.isOpened():
            logger.error("Could not open camera for vision service")
            self.running = False
            return

        # Standard resolution for better field of view
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while self.running:
            success, img = cap.read()
            if not success:
                time.sleep(0.1)
                continue
                
            # Don't flip - keep natural camera orientation for correct tracking direction
            # img = cv2.flip(img, 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            try:
                results = self.hands.process(img_rgb)
                
                if results.multi_hand_landmarks:
                    # Get first hand
                    hand = results.multi_hand_landmarks[0]
                    
                    # Track Index Finger Tip (Landmark 8)
                    landmark = hand.landmark[8]
                    x_norm = landmark.x
                    y_norm = landmark.y
                    print(f"✋ Hand detected: x={x_norm:.2f}, y={y_norm:.2f}")
                    
                    # Check for Fist (Lock Gesture)
                    # Count fingers: Check if fingertips are below PIP joints
                    fingers_closed = 0
                    # Index (8 vs 6)
                    if hand.landmark[8].y > hand.landmark[6].y: fingers_closed += 1
                    # Middle (12 vs 10)
                    if hand.landmark[12].y > hand.landmark[10].y: fingers_closed += 1
                    # Ring (16 vs 14)
                    if hand.landmark[16].y > hand.landmark[14].y: fingers_closed += 1
                    # Pinky (20 vs 18)
                    if hand.landmark[20].y > hand.landmark[18].y: fingers_closed += 1
                    
                    print(f"👆 Fingers closed: {fingers_closed}/4, locked={self.locked}")
                    
                    # Gesture detection (always runs)
                    if fingers_closed >= 3:
                        # Fist = BRAKE / PAUSE
                        if not self.locked:
                            self.locked = True
                            logger.info("🔒 Fist detected: Pausing tracking")
                    else:
                        # Open Hand = TRACK
                        if self.locked:
                            self.locked = False
                            logger.info("🔓 Hand open: Resuming tracking")

                    # If locked, skip motor updates but continue detection loop
                    if self.locked:
                        time.sleep(0.05)
                        continue

                    # Motor Mapping
                    # X: 0.0(Left) -> 1.0(Right)
                    # Positive = lamp follows hand direction
                    raw_yaw = (x_norm - 0.5) * 120  # Removed negative sign
                    
                    # Pitch: Map 0.0-1.0
                    # Positive = lamp follows hand up/down
                    raw_pitch = (0.5 - y_norm) * 80  # Removed negative sign
                    
                    # Smoothing
                    self.smooth_yaw = (self.smooth_yaw * (1-self.alpha)) + (raw_yaw * self.alpha)
                    self.smooth_pitch = (self.smooth_pitch * (1-self.alpha)) + (raw_pitch * self.alpha)
                    
                    self._update_motors(self.smooth_yaw, self.smooth_pitch)
                    print(f"🎯 Motor update: yaw={self.smooth_yaw:.1f}, pitch={self.smooth_pitch:.1f}")
                    
            except Exception as e:
                logger.error(f"MediaPipe error: {e}")
                time.sleep(0.5)
                
            time.sleep(0.01)
            
        cap.release()
        
    def _update_motors(self, yaw_deg, pitch_deg):
        if not self.motor_service:
            print("❌ No motor service available")
            return
        
        # Base Yaw
        yaw_offset = self.motor_service.offsets.get('base_yaw', 2048)
        yaw_pos = int(yaw_offset + (yaw_deg / 180.0) * 2048)
        print(f"🔧 Sending Motor 1 (yaw): offset={yaw_offset}, pos={yaw_pos}")
        self.motor_service._set_position(1, yaw_pos)
        
        # Pitch Logic (Inverse Kinematics approx)
        k_base = -0.5
        k_elbow = 0.8
        k_wrist = -0.3
        
        bp_offset = self.motor_service.offsets.get('base_pitch', 2048)
        bp_pos = int(bp_offset + (pitch_deg * k_base / 180.0) * 2048)
        self.motor_service._set_position(2, bp_pos)
        
        ep_offset = self.motor_service.offsets.get('elbow_pitch', 2048)
        ep_pos = int(ep_offset + (pitch_deg * k_elbow / 180.0) * 2048)
        self.motor_service._set_position(3, ep_pos)
        
        wp_offset = self.motor_service.offsets.get('wrist_pitch', 2048)
        wp_pos = int(wp_offset + (pitch_deg * k_wrist / 180.0) * 2048)
        self.motor_service._set_position(5, wp_pos)
