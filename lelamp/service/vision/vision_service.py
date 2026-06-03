"""Vision Service - MediaPipe Hand Tracking"""

import cv2
import time
import threading
import logging

# Try standard mediapipe first (works with both regular and mediapipe-rpi4)
try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    mp = None
    MEDIAPIPE_AVAILABLE = False

logger = logging.getLogger(__name__)

class VisionService:
    """Tracks hand using MediaPipe hand detection.

    Hardware topology: 4 motors. Motor 3 (elbow_pitch) was physically removed;
    motor 2 (base_pitch) is now at the old elbow position and carries all the
    pitch motion. Motor 4 (wrist_roll) tilts the head sideways toward the hand
    for a more lifelike "curious" follow.
    """

    # Motor IDs after the 5→4 conversion. Keep in sync with
    # DirectMotorsService.MOTOR_IDS.
    MOTOR_BASE_YAW   = 1
    MOTOR_BASE_PITCH = 2
    MOTOR_WRIST_ROLL = 4
    MOTOR_WRIST_PITCH = 5

    # Gain coefficients — empirically tuned for the single-joint arm.
    # Negative signs depend on motor mount orientation; flip if the lamp
    # moves the wrong way during hand tracking.
    K_BASE_PITCH  = -1.0   # base_pitch carries the arm pitch alone
    K_WRIST_PITCH = -0.3   # small head tilt for "looking at" the hand
    K_WRIST_ROLL  = 0.15   # subtle head-tilt sideways toward the hand

    def __init__(self, motor_service=None, camera_index=0):
        if not MEDIAPIPE_AVAILABLE:
            raise ImportError("MediaPipe not available")
            
        self.motor_service = motor_service
        self.camera_index = camera_index
        self.running = False
        self.thread = None
        
        # MediaPipe Setup
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            model_complexity=0,  # 0 = Fastest (essential for Pi), 1 = Accurate
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
        
        print("📷 Camera opened for hand tracking")
        
        while self.running:
            success, img = cap.read()
            if not success:
                time.sleep(0.1)
                continue
                
            # Flip for mirror effect
            img = cv2.flip(img, 1)
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
                    fingers_closed = 0
                    if hand.landmark[8].y > hand.landmark[6].y: fingers_closed += 1
                    if hand.landmark[12].y > hand.landmark[10].y: fingers_closed += 1
                    if hand.landmark[16].y > hand.landmark[14].y: fingers_closed += 1
                    if hand.landmark[20].y > hand.landmark[18].y: fingers_closed += 1
                    
                    print(f"👆 Fingers closed: {fingers_closed}/4, locked={self.locked}")
                    
                    # Gesture detection
                    if fingers_closed >= 3:
                        if not self.locked:
                            self.locked = True
                            print("🔒 Fist detected: Pausing tracking")
                    else:
                        if self.locked:
                            self.locked = False
                            print("🔓 Hand open: Resuming tracking")

                    if self.locked:
                        time.sleep(0.05)
                        continue

                    # Motor Mapping - lamp follows hand direction
                    raw_yaw = (x_norm - 0.5) * 120
                    raw_pitch = (0.5 - y_norm) * 80
                    
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

        svc = self.motor_service

        def drive(motor_id, offset_name, gain, axis_deg):
            offset = svc.offsets.get(offset_name, 2048)
            pos = int(offset + (axis_deg * gain / 180.0) * 2048)
            # _set_position clamps to 0..4095 internally; clamp here too so
            # we can detect when we're hitting a soft limit.
            clamped = max(0, min(4095, pos))
            if clamped != pos:
                logger.debug(f"{offset_name} clamped: {pos} -> {clamped}")
            svc._set_position(motor_id, clamped)

        # Base Yaw — primary horizontal tracking.
        drive(self.MOTOR_BASE_YAW, 'base_yaw', 1.0, yaw_deg)

        # Pitch — single-joint arm: base_pitch does the heavy work,
        # wrist_pitch adds a small head tilt so the lamp looks at the hand.
        drive(self.MOTOR_BASE_PITCH,  'base_pitch',  self.K_BASE_PITCH,  pitch_deg)
        drive(self.MOTOR_WRIST_PITCH, 'wrist_pitch', self.K_WRIST_PITCH, pitch_deg)

        # Wrist Roll — banks the head sideways toward the hand for a
        # curious "watching you" feel. Tiny gain; flip sign if it tilts away.
        drive(self.MOTOR_WRIST_ROLL,  'wrist_roll',  self.K_WRIST_ROLL,  yaw_deg)
