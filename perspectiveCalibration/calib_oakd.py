import cv2
import depthai as dai
import numpy as np
import pickle
import math

print("Mark corners of the warp in this specific order:")
print("TOP_LEFT, BOT_LEFT, BOT_RIGHT, TOP_RIGHT")\

# store warp box corners
corners = []
warped = False
colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]

# mouse callback
def get_mouse_position(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN and not warped:
        corners.append((x, y))

# create pipeline
pipeline = dai.Pipeline()
cam = pipeline.create(dai.node.ColorCamera)
cam.setColorOrder(dai.ColorCameraProperties.ColorOrder.RGB)

# preview size has to match nn input in order to work in app.py
cam.setPreviewSize(416, 416)
xout = pipeline.create(dai.node.XLinkOut)
xout.setStreamName("rgb")
cam.preview.link(xout.input)

with dai.Device(pipeline) as device:

    qRgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)

    while True:
        # get frame
        inPreview = qRgb.get()
        frame = inPreview.getCvFrame()

        if corners:
            for index, corner in enumerate(corners):
                cv2.circle(frame, corner, 5, colors[index], -1)
                
            frame = cv2.putText(
                img=frame,
                text="Mark conrners of the warp in this order:",
                org=(10, 20),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=0.5,
                color=(0, 255, 0),
                thickness=1
            )
            frame = cv2.putText(
                img=frame,
                text="TOP_LEFT, BOT_LEFT, BOT_RIGHT, TOP_RIGHT",
                org=(10, 40),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=0.5,
                color=(0, 255, 0),
                thickness=1
            )

        cv2.imshow("frame", frame)
        cv2.setMouseCallback('frame', get_mouse_position)

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
            transform_matrix = cv2.getPerspectiveTransform(point_matrix, convert_matrix)
            warped = True

        elif warped:
            img_warped = cv2.warpPerspective(frame, transform_matrix, (w, h))
            img_warped = cv2.putText(
                img=img_warped,
                text="If the warp is correct press y,",
                org=(20, 20),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=0.5,
                color=(0, 255, 0),
                thickness=1
            )
            img_warped = cv2.putText(
                img=img_warped,
                text="otherwise press n",
                org=(20, 40),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=0.5,
                color=(0, 255, 0),
                thickness=1
            )
            cv2.imshow("warped", img_warped)

            if cv2.waitKey(1) & 0xFF == ord("y"):
                with open("calibration_result", "wb") as outfile:
                    pickle.dump(transform_matrix, outfile)
                break

            elif cv2.waitKey(1) & 0xFF == ord("n"):
                corners = []
                warped = False

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

cv2.destroyAllWindows()
