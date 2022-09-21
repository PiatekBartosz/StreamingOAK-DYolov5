import cv2
import numpy as np

img = cv2.imread("test.jpg")

# Pixel values in original image
red_point = [147, 150]
green_point = [256, 182]
black_point = [119, 453]
blue_point = [231, 460]

# Create point matrix
point_matrix = np.float32([red_point, green_point, black_point, blue_point])

# Draw circle for each point
cv2.circle(img, (red_point[0], red_point[1]), 10, (0, 0, 255), cv2.FILLED)
cv2.circle(img, (green_point[0], green_point[1]), 10, (0, 255, 0), cv2.FILLED)
cv2.circle(img, (blue_point[0], blue_point[1]), 10, (255, 0, 0), cv2.FILLED)
cv2.circle(img, (black_point[0], black_point[1]), 10, (0, 0, 0), cv2.FILLED)

# Output image size
width, height = 250, 350

# Desired points value in output images
converted_red_pixel_value = [0, 0]
converted_green_pixel_value = [width, 0]
converted_black_pixel_value = [0, height]
converted_blue_pixel_value = [width, height]

# Convert points
converted_points = np.float32([converted_red_pixel_value, converted_green_pixel_value,
                               converted_black_pixel_value, converted_blue_pixel_value])

# perspective transform
perspective_transform = cv2.getPerspectiveTransform(point_matrix, converted_points)
img_Output = cv2.warpPerspective(img, perspective_transform, (width, height))

cv2.imshow("Original Image", img)
cv2.imshow("Output Image", img_Output)
cv2.waitKey(0)