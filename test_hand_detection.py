"""
Hand Detection Test - Shows camera feed with hand landmarks
Press 'q' to quit
"""
import cv2
import mediapipe as mp

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Open camera
cap = cv2.VideoCapture(0)

print("🎥 Camera opened. Show your hand to the camera!")
print("Press 'q' to quit")

while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Camera read failed")
        continue
    
    # Flip for mirror effect
    image = cv2.flip(image, 1)
    
    # Convert to RGB for MediaPipe
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)
    
    # Draw hand landmarks
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Draw landmarks
            mp_drawing.draw_landmarks(
                image, 
                hand_landmarks, 
                mp_hands.HAND_CONNECTIONS
            )
            
            # Get index finger tip position
            index_tip = hand_landmarks.landmark[8]
            x = int(index_tip.x * image.shape[1])
            y = int(index_tip.y * image.shape[0])
            
            # Draw circle at index finger
            cv2.circle(image, (x, y), 15, (0, 255, 0), -1)
            
            # Show coordinates
            cv2.putText(image, f"Hand: x={index_tip.x:.2f}, y={index_tip.y:.2f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            print(f"✋ Hand detected at x={index_tip.x:.2f}, y={index_tip.y:.2f}")
    else:
        cv2.putText(image, "No hand detected", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    
    # Show image
    cv2.imshow('Hand Detection Test', image)
    
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("✅ Test complete")
