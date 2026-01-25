#!/usr/bin/env python3
"""Test Blue Color Tracking with Camera Preview

Run this script to see what the camera detects as blue.
The preview shows:
- Green rectangle: Detected blue object
- Red dot: Center point being tracked
- White mask: What's detected as blue

Press 'q' to quit.
"""

import cv2
import numpy as np

def main():
    print("🔵 Blue Color Tracking Test")
    print("Press 'q' to quit\n")
    
    # HSV range for blue
    blue_lower = np.array([100, 100, 50])
    blue_upper = np.array([130, 255, 255])
    min_area = 5000
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ Could not open camera")
        return
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"📷 Camera: {width}x{height}")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Create blue mask
        mask = cv2.inRange(hsv, blue_lower, blue_upper)
        
        # Clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            
            if area > min_area:
                x, y, w, h = cv2.boundingRect(largest)
                cx, cy = x + w // 2, y + h // 2
                
                # Draw on frame
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                cv2.circle(frame, (cx, cy), 8, (0, 0, 255), -1)
                
                # Calculate normalized position
                x_norm = cx / width
                y_norm = cy / height
                yaw = (x_norm - 0.5) * 80
                pitch = (0.5 - y_norm) * 50
                
                cv2.putText(frame, f"Blue: {area:.0f}px", (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.putText(frame, f"Yaw: {yaw:.1f} Pitch: {pitch:.1f}", (10, 60),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                print(f"\r🔵 x={x_norm:.2f} y={y_norm:.2f} area={area:.0f} yaw={yaw:.1f} pitch={pitch:.1f}   ", end="")
        
        cv2.putText(frame, "Blue Color Tracking Test", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow("Camera", frame)
        cv2.imshow("Blue Mask", mask)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("\n✅ Done")

if __name__ == "__main__":
    main()
