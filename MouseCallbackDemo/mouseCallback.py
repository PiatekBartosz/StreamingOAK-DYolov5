import numpy as np
import cv2

# mouse callback function
def draw_circle(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDBLCLK:
        cv2.circle(img, (x, y), 100, (255, 0, 0), -1)
        print(f"MOUSE X: {x}")
        print(f"MOUSE Y: {y}")

# setting callibration point

# create a black image, la window and bind the function to window
# cap = cv2.cap
img = np.zeros((512, 512, 3), np.uint8)
cv2.namedWindow('image')
cv2.setMouseCallback('image', draw_circle)

while True:
    cv2.imshow('image', img)
    if cv2.waitKey(1) == ord('q'):
        break

cv2.destroyAllWindows()
