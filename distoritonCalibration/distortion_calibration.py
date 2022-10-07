import numpy as np
import cv2 as cv
import time as t
import glob
import json

# settings
chessboard_size = (5, 8)

# termination criteria
criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# prepare object points shaped [[0. 0. 0.], [1. 0. 0.], [0. 0. 0.], ... , [chessboard_size[0]. chessboard_size[1]. 0.]}
objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)

# prepare list to store img points
obj_points = []  # 3D points in real world
img_points = []  # 2D points on captured frame

# get path and name for all jpgs
images = glob.glob('distoritonCalibration/calibraion photos/*.jpg')

for location in images:
    img = cv.imread(location)
    img_gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

    # find the chessboard corners
    ret, corners = cv.findChessboardCorners(img_gray, (chessboard_size[0], chessboard_size[1]), None)

    if ret:
        obj_points.append(objp)

        corners2 = cv.cornerSubPix(img_gray, corners, (11, 11), (-1, -1), criteria)
        img_points.append(corners)

        cv.drawChessboardCorners(img, (chessboard_size[0], chessboard_size[1]), corners2, ret)

        ret, camera_matrix, distortion, rotation_vectors, translation_vectors = cv.calibrateCamera(obj_points,
                                                                                                   img_points,
                                                                                                   img.shape[:2], None,
                                                                                                   None)

        cv.imshow('CameraCalibration', img)
        cv.waitKey(200)

# undistort the image
for img in images:
    img = cv.imread(img)
    h, w = img.shape[:2]
    new_camera_matrix, roi = cv.getOptimalNewCameraMatrix(camera_matrix, distortion, (w, h), 1, (w, h))
    dst = cv.undistort(img, camera_matrix, distortion, None, new_camera_matrix)

    # crop the img
    x, y, w, h = roi
    dst = dst[y:y + h, x:x + w]

    cv.imshow("Calibratied img", dst)
    cv.waitKey(500)

cv.destroyAllWindows()

# # save camera calibration data to json file
# data = {"ret": ret, "camera_matrix": camera_matrix.tolist(), "dist": distortion.tolist()}
#
# fname = "CameraCalibrationData.json"
#
# with open(fname, "w") as f:
#     json.dump(data, f)

