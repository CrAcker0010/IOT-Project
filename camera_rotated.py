import cv2

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open camera.")
    exit()

print("Press 'q' to quit.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: Failed to read frame.")
        break

    # Rotate 90 degrees anticlockwise
    rotated = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

    cv2.imshow("Camera - Rotated 90 CCW", rotated)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
