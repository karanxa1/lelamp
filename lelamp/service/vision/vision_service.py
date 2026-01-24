"""Vision Service - Hand Tracking using MediaPipe Solutions API (Pi compatible)"""

import cv2
import mediapipe as mp
import time
import threading
import logging
import os

logger = logging.getLogger(__name__)

class VisionService:
    def __init__(self, motor_service=None, camera_index=0):
        self.motor_service = motor_service
        self.camera_index = camera_index
        self.running = False
        self.thread = None
        
        # Smoothing (Exponential Moving Average)
        self.alpha = 0.3  # 0.0 = no movement, 1.0 = instant
        self.smooth_yaw = 0.0
        self.smooth_pitch = 0.0
        
        # MediaPipe Solutions (more compatible with Pi)
        self.mp_hands = mp.solutions.hands

    def start(self):
        """Start tracking thread"""
        if self.running: return
        
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        # Disable idle animation when hand tracking starts
        if self.motor_service:
            self.motor_service._is_animating = True
            
        logger.info("Vision Service started")

    def stop(self):
        """Stop tracking"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            
        # Re-enable idle animation
        if self.motor_service:
            self.motor_service._is_animating = False
            
        logger.info("Vision Service stopped")

    def _is_fist(self, landmarks):
        """Check if hand is a fist (fingertips close to wrist)"""
        wrist = landmarks.landmark[0]
        tips = [8, 12, 16, 20]  # Index, Middle, Ring, Pinky tips
        
        curled_count = 0
        for tip_idx in tips:
            tip = landmarks.landmark[tip_idx]
            dist = ((tip.x - wrist.x)**2 + (tip.y - wrist.y)**2)**0.5
            if dist < 0.25:
                curled_count += 1
        
        return curled_count >= 3

    def _tracking_loop(self):
        """Main tracking loop using Solutions API"""
        cap = cv2.VideoCapture(self.camera_index)
        
        if not cap.isOpened():
            logger.error("Failed to open camera")
            self.running = False
            return
        
        # Use Solutions API (works on Pi)
        with self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        ) as hands:
            
            while self.running:
                success, img = cap.read()
                if not success:
                    logger.warning("Camera failed to read")
                    time.sleep(0.5)
                    continue

                # Flip for mirror view
                img = cv2.flip(img, 1)
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                
                # Process
                results = hands.process(img_rgb)
                
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # Check for fist gesture (Lock)
                        if self._is_fist(hand_landmarks):
                            continue
                            
                        # Index Finger Tip (Index 8)
                        idx_tip = hand_landmarks.landmark[8]
                        
                        # X Axis (0.0 Left -> 1.0 Right)
                        # Map to Yaw: -60 (Left) to +60 (Right)
                        raw_yaw = (idx_tip.x - 0.5) * 120
                        
                        # Y Axis (0.0 Top -> 1.0 Bottom)
                        # Map to Pitch: +40 (Up) to -40 (Down)
                        raw_pitch = (0.5 - idx_tip.y) * 80
                        
                        # Smoothing
                        self.smooth_yaw = (self.smooth_yaw * (1-self.alpha)) + (raw_yaw * self.alpha)
                        self.smooth_pitch = (self.smooth_pitch * (1-self.alpha)) + (raw_pitch * self.alpha)
                        
                        # Send to motors
                        if self.motor_service:
                            self._update_motors(self.smooth_yaw, self.smooth_pitch)

                time.sleep(0.01)  # ~100 FPS cap

        cap.release()

    def _update_motors(self, yaw_deg, pitch_deg):
        """Convert degrees to motor positions"""
        if not self.motor_service: return
        
        # Base Yaw
        yaw_offset = self.motor_service.offsets.get('base_yaw', 2048)
        yaw_pos = int(yaw_offset + (yaw_deg / 180.0) * 2048)
        self.motor_service._set_position(1, yaw_pos)
        
        # Pitch (Up/Down) - coordinated movement
        k_base = -0.5
        k_elbow = 0.8
        k_wrist = -0.3
        
        # Base Pitch
        bp_offset = self.motor_service.offsets.get('base_pitch', 2048)
        bp_pos = int(bp_offset + (pitch_deg * k_base / 180.0) * 2048)
        self.motor_service._set_position(2, bp_pos)
        
        # Elbow Pitch
        ep_offset = self.motor_service.offsets.get('elbow_pitch', 2048)
        ep_pos = int(ep_offset + (pitch_deg * k_elbow / 180.0) * 2048)
        self.motor_service._set_position(3, ep_pos)
        
        # Wrist Pitch
        wp_offset = self.motor_service.offsets.get('wrist_pitch', 2048)
        wp_pos = int(wp_offset + (pitch_deg * k_wrist / 180.0) * 2048)
        self.motor_service._set_position(5, wp_pos)
