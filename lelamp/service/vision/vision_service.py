"""Vision Service - Blue Color Object Tracking"""

import cv2
import time
import threading
import logging
import numpy as np

logger = logging.getLogger(__name__)

class VisionService:
    """Tracks blue colored objects using OpenCV HSV color detection"""
    
    def __init__(self, motor_service=None, camera_index=0):
        self.motor_service = motor_service
        self.camera_index = camera_index
        self.running = False
        self.thread = None
        
        # HSV range for blue color detection (adjust if needed)
        # Blue range: H=100-130, S=100-255, V=50-255
        self.blue_lower = np.array([100, 100, 50])
        self.blue_upper = np.array([130, 255, 255])
        
        # Minimum contour area (filters out noise)
        self.min_contour_area = 500
        
        # Tracking State
        self.smooth_yaw = 0.0
        self.smooth_pitch = 0.0
        self.alpha = 0.3  # Smoothing factor (higher = more responsive)
        
        # Frame dimensions (set when camera opens)
        self.frame_width = 640
        self.frame_height = 480
        
    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        
        if self.motor_service:
            self.motor_service._is_animating = True
        logger.info("Vision Service started (Blue Color Tracking)")
        print("🔵 Blue color tracking started")
        
    def stop(self):
        self.running = False
        if self.thread: self.thread.join(timeout=1.0)
        if self.motor_service:
            self.motor_service._is_animating = False
        logger.info("Vision Service stopped")
        print("🔵 Blue color tracking stopped")
        
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
            print("❌ Could not open camera")
            self.running = False
            return

        # Set camera resolution
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Get actual dimensions
        self.frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"📷 Camera opened: {self.frame_width}x{self.frame_height}")
        
        frame_count = 0
        while self.running:
            success, frame = cap.read()
            if not success:
                time.sleep(0.1)
                continue
            
            frame_count += 1
            
            try:
                # Convert to HSV color space
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                
                # Create mask for blue color
                mask = cv2.inRange(hsv, self.blue_lower, self.blue_upper)
                
                # Apply morphological operations to clean up the mask
                kernel = np.ones((5, 5), np.uint8)
                mask = cv2.erode(mask, kernel, iterations=1)
                mask = cv2.dilate(mask, kernel, iterations=2)
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    # Find the largest blue contour
                    largest_contour = max(contours, key=cv2.contourArea)
                    area = cv2.contourArea(largest_contour)
                    
                    if area > self.min_contour_area:
                        # Get bounding box and center
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        center_x = x + w // 2
                        center_y = y + h // 2
                        
                        # Normalize to 0.0 - 1.0
                        x_norm = center_x / self.frame_width
                        y_norm = center_y / self.frame_height
                        
                        # Print detection every 10 frames to reduce spam
                        if frame_count % 10 == 0:
                            print(f"🔵 Blue detected: x={x_norm:.2f}, y={y_norm:.2f}, area={area:.0f}")
                        
                        # Motor Mapping
                        # X: 0.0(Left) -> 1.0(Right)
                        raw_yaw = (x_norm - 0.5) * 120
                        
                        # Pitch: Map 0.0(Top) -> 1.0(Bottom)
                        raw_pitch = (0.5 - y_norm) * 80
                        
                        # Smoothing
                        self.smooth_yaw = (self.smooth_yaw * (1-self.alpha)) + (raw_yaw * self.alpha)
                        self.smooth_pitch = (self.smooth_pitch * (1-self.alpha)) + (raw_pitch * self.alpha)
                        
                        self._update_motors(self.smooth_yaw, self.smooth_pitch)
                        
                        if frame_count % 10 == 0:
                            print(f"🎯 Motor: yaw={self.smooth_yaw:.1f}, pitch={self.smooth_pitch:.1f}")
                    
            except Exception as e:
                logger.error(f"Color tracking error: {e}")
                print(f"❌ Error: {e}")
                time.sleep(0.5)
                
            time.sleep(0.02)  # ~50 FPS
            
        cap.release()
        
    def _update_motors(self, yaw_deg, pitch_deg):
        if not self.motor_service:
            return
        
        # Base Yaw (Motor 1)
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
