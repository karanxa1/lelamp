"""Vision Service - MediaPipe TFLite Hand Tracking"""

import cv2
import mediapipe as mp
import time
import threading
import logging

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self, motor_service=None, camera_index=0):
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
        cap = cv2.VideoCapture(self.camera_index)
        # Low res for performance on Pi
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        
        while self.running:
            success, img = cap.read()
            if not success:
                time.sleep(0.1)
                continue
                
            img = cv2.flip(img, 1)
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            try:
                results = self.hands.process(img_rgb)
                
                if results.multi_hand_landmarks and not self.locked:
                    # Get first hand
                    hand = results.multi_hand_landmarks[0]
                    
                    # Track Index Finger Tip (Landmark 8)
                    landmark = hand.landmark[8]
                    x_norm = landmark.x
                    y_norm = landmark.y
                    
                    # Check for Fist (Lock Gesture)
                    # If Finger Tip (8) is below Finger PIP (6), it's curled
                    if hand.landmark[8].y > hand.landmark[6].y:
                        logger.info("Gesture: Fist detected (Locking)")
                        # Could toggle lock here, but for now just log
                    
                    # Motor Mapping
                    # X: 0.0(Left) -> 1.0(Right). Motors: -ve -> +ve
                    # Yaw: Map 0.0-1.0 to -50deg to +50deg
                    raw_yaw = (x_norm - 0.5) * 100
                    
                    # Pitch: Map 0.0-1.0 to +40deg to -40deg
                    raw_pitch = (0.5 - y_norm) * 80
                    
                    # Smoothing
                    self.smooth_yaw = (self.smooth_yaw * (1-self.alpha)) + (raw_yaw * self.alpha)
                    self.smooth_pitch = (self.smooth_pitch * (1-self.alpha)) + (raw_pitch * self.alpha)
                    
                    self._update_motors(self.smooth_yaw, self.smooth_pitch)
                    
            except Exception as e:
                logger.error(f"MediaPipe error: {e}")
                time.sleep(0.5)
                
            time.sleep(0.01)
            
        cap.release()
        
    def _update_motors(self, yaw_deg, pitch_deg):
        if not self.motor_service: return
        
        # Base Yaw
        yaw_offset = self.motor_service.offsets.get('base_yaw', 2048)
        yaw_pos = int(yaw_offset + (yaw_deg / 180.0) * 2048)
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
