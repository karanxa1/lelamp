"""Lightweight Vision Service - Uses Color Tracking (No Heavy ML)"""

import cv2
import numpy as np
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
        
        # Tracking center
        self.smooth_yaw = 0.0
        self.smooth_pitch = 0.0
        self.alpha = 0.2
        
        # Skin color range (YCrCb color space is better for skin)
        # These values work for many skin tones but may need tuning
        self.min_YCrCb = np.array([0, 133, 77], np.uint8)
        self.max_YCrCb = np.array([235, 173, 127], np.uint8)

    def start(self):
        """Start tracking thread"""
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        if self.motor_service:
            self.motor_service._is_animating = True
        logger.info("Lightweight Vision Service started")

    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1.0)
        if self.motor_service:
            self.motor_service._is_animating = False
        logger.info("Vision Service stopped")

    def _tracking_loop(self):
        cap = cv2.VideoCapture(self.camera_index)
        
        while self.running:
            success, img = cap.read()
            if not success:
                time.sleep(0.5)
                continue

            # Flip & Blur
            img = cv2.flip(img, 1)
            img = cv2.GaussianBlur(img, (5, 5), 0)
            
            # Convert to YCrCb
            ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
            
            # Create Mask
            mask = cv2.inRange(ycrcb, self.min_YCrCb, self.max_YCrCb)
            
            # Clean up mask
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            mask = cv2.erode(mask, kernel, iterations=2)
            mask = cv2.dilate(mask, kernel, iterations=2)
            
            # Find largest contour
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                max_contour = max(contours, key=cv2.contourArea)
                
                # Filter small noise
                if cv2.contourArea(max_contour) > 2000:
                    # Find top-most point (fingertip approximation)
                    top_point = tuple(max_contour[max_contour[:, :, 1].argmin()][0])
                    
                    # Normalize (0.0 - 1.0)
                    h, w, _ = img.shape
                    x_norm = top_point[0] / w
                    y_norm = top_point[1] / h
                    
                    # Convert to Motor Degrees
                    raw_yaw = (x_norm - 0.5) * 100
                    raw_pitch = (0.5 - y_norm) * 80
                    
                    # Smooth
                    self.smooth_yaw = (self.smooth_yaw * (1-self.alpha)) + (raw_yaw * self.alpha)
                    self.smooth_pitch = (self.smooth_pitch * (1-self.alpha)) + (raw_pitch * self.alpha)
                    
                    # Update Motors
                    if self.motor_service:
                        self._update_motors(self.smooth_yaw, self.smooth_pitch)

            time.sleep(0.03)

        cap.release()

    def _update_motors(self, yaw_deg, pitch_deg):
        """Convert degrees to motor positions (Logic copied from original service)"""
        if not self.motor_service: return
        
        # Base Yaw
        yaw_offset = self.motor_service.offsets.get('base_yaw', 2048)
        yaw_pos = int(yaw_offset + (yaw_deg / 180.0) * 2048)
        self.motor_service._set_position(1, yaw_pos)
        
        # Pitch Mapping
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
