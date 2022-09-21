import cv2
import numpy as np

print("Mark corners of the warp in this specific order:")
print("TOP_LEFT, BOT_LEFT, BOT_RIGHT, TOP_RIGHT")

# store warp box corners
corners = []
warped = False

# mouse callback
def get_mouse_position(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and not warped:
        corners.append((x, y))

cap = cv2.VideoCapture(0)

while True:

    ret, frame = cap.read()

    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]

    if corners:
        for index, corner in enumerate(corners):
            cv2.circle(frame, corner, 10, colors[index], -1)

    cv2.imshow('frame', frame)
    cv2.setMouseCallback('frame', get_mouse_position)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    if len(corners) == 4 and not warped:

        # create point matrix1
        top_left = [corners[0][0], corners[0][1]]
        bot_left = [corners[1][0], corners[1][1]]
        bot_right = [corners[2][0], corners[2][1]]
        top_right = [corners[3][0], corners[3][1]]

        # convert matrix
        h, w, _ = frame.shape
        convert_matrix = np.float32([[0, 0], [0, h], [w, h], [w, 0]])
        point_matrix = np.float32([top_left, bot_left, bot_right, top_right])

        # search for max height
        h1 = np.sqrt((top_left[0] - bot_left[0]) ** 2 + (top_left[1] - bot_left[1]) ** 2)
        h2 = np.sqrt((top_right[0] - bot_right[0]) ** 2 + (top_right[1] - bot_right[1]) ** 2)
        max_height = max(int(h1), int(h2))

        w1 = np.sqrt((top_left[0] - top_right[0]) ** 2 + (top_left[1] - top_right[1]) ** 2)
        w2 = np.sqrt((bot_left[0] - bot_right[0]) ** 2 + (bot_left[1] - bot_right[1]) ** 2)
        max_width = max(int(w1), int(w2))

        perspective_transform = cv2.getPerspectiveTransform(point_matrix, convert_matrix)
        img_warped = cv2.warpPerspective(frame, perspective_transform, (max_width, max_height))
        cv2.imshow("warped", img_warped)
        warped = True
cap.release()
cv2.destroyAllWindows()
