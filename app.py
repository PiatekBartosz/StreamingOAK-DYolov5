import json
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import depthai as dai
import cv2
from PIL import Image
from pathlib import Path
import numpy as np
import pickle
import select
import socket
import argparse
from helpers.server_classes import TCPServerRequest, VideoStreamHandler, ThreadedHTTPServer

"""
   Parsing arguments 
"""

parser = argparse.ArgumentParser()
parser.add_argument("-d", "--device", help="Choose host: \n0 - delta simulation\n1 - real delta",
                    type=int, choices=[0, 1], default=0)
parser.add_argument("-i", "--ip", help="Set http and json servers ip-s. The default ip would be localhost",
                    type=str, default='localhost')
parser.add_argument("-p", "--preview", help="Choose preview: \n0 - preview off\n1 - preview on",
                    type=int, choices=[0, 1], default=1)

args = parser.parse_args()

# PORTS
HTTP_SERVER_PORT = 8090
HTTP_SERVER_PORT2 = 8080
HTTP_SERVER_PORT3 = 8070
JSON_PORT = 8060

if args.device == 0:
    delta_host, delta_port = "127.0.0.1", 2137
else:
    delta_host, delta_port = "192.168.0.155", 10

IPAddress = args.ip

if args.preview:
    preview = True
else:
    preview = False

"""
    Define pipeline & nodes
"""

pipeline = dai.Pipeline()

yoloSpatial = pipeline.create(dai.node.YoloSpatialDetectionNetwork)
camRgb = pipeline.create(dai.node.ColorCamera)
monoLeft = pipeline.create(dai.node.MonoCamera)
monoRight = pipeline.create(dai.node.MonoCamera)
stereo = pipeline.create(dai.node.StereoDepth)

# outputs nodes
nnNetworkOut = pipeline.create(dai.node.XLinkOut)
xoutRgb = pipeline.create(dai.node.XLinkOut)
xoutNN = pipeline.create(dai.node.XLinkOut)
xoutDepth = pipeline.create(dai.node.XLinkOut)

xoutRgb.setStreamName("rgb")
xoutNN.setStreamName("detections")
xoutDepth.setStreamName("depth")
nnNetworkOut.setStreamName("nnNetwork")

"""
    Define pipeline nodes properties
"""

# nodes properties
camRgb.setPreviewSize(416, 416)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
camRgb.setInterleaved(False)
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
camRgb.setFps(40)

monoLeft.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoLeft.setCamera("left")
monoRight.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
monoRight.setCamera("right")

# setting node configs
stereo.setDefaultProfilePreset(dai.node.StereoDepth.PresetMode.HIGH_DENSITY)

# Align depth map to the perspective of RGB camera, on which inference is done
stereo.setDepthAlign(dai.CameraBoardSocket.CAM_A)
stereo.setOutputSize(monoLeft.getResolutionWidth(), monoLeft.getResolutionHeight())
stereo.setSubpixel(True)

"""
    Configure Yolo NN model
"""

# blob model path
yoloSpatial.setBlobPath(Path("config/yoloModel.blob"))

# open NN config
configPath = Path("config/yoloConfig.json")

if not configPath.exists():
    raise ValueError(f"Path {configPath} does not exist!")

print("Loading Yolo config...")
with open(configPath) as file:
    config = json.load(file)
nnConfig = config["nn_config"]
if nnConfig:
    print("Successfully loaded config")

# spatial Yolo detection parameters
yoloSpatial.input.setBlocking(False)
yoloSpatial.setBoundingBoxScaleFactor(0.5)
yoloSpatial.setDepthLowerThreshold(100) # Min 10 centimeters
yoloSpatial.setDepthUpperThreshold(5000) # Max 5 meters

# configure Yolo
yoloSpatial.setNumClasses(nnConfig["NN_specific_metadata"]["classes"])
yoloSpatial.setCoordinateSize(nnConfig["NN_specific_metadata"]["coordinates"])
yoloSpatial.setAnchors(nnConfig["NN_specific_metadata"]["anchors"])
yoloSpatial.setAnchorMasks(nnConfig["NN_specific_metadata"]["anchor_masks"])
yoloSpatial.setIouThreshold(nnConfig["NN_specific_metadata"]["iou_threshold"])
yoloSpatial.setConfidenceThreshold(nnConfig["NN_specific_metadata"]["confidence_threshold"])

# get labels
labels = config["mappings"]["labels"]

"""
    Link pipeline nodes
"""

monoLeft.out.link(stereo.left)
monoRight.out.link(stereo.right)

camRgb.preview.link(yoloSpatial.input)
yoloSpatial.passthrough.link(xoutRgb.input)  # TODO should be sync with detection ?

yoloSpatial.out.link(xoutNN.input)

stereo.depth.link(yoloSpatial.inputDepth)
yoloSpatial.passthroughDepth.link(xoutDepth.input)
yoloSpatial.outNetwork.link(nnNetworkOut.input)

"""
    Start servers
"""

# # start TCP data server (JSON)
# try:
#     server_TCP = socketserver.TCPServer(("127.0.0.1", JSON_PORT), TCPServerRequest)
#     th = threading.Thread(target=server_TCP.serve_forever)
#     th.daemon = True
#     th.start()
# except Exception as e:
#     print(e)

# start MJPEG HTTP Servers
try:
    server_HTTP = ThreadedHTTPServer((args.ip, HTTP_SERVER_PORT), VideoStreamHandler)
    th2 = threading.Thread(target=server_HTTP.serve_forever)
    th2.daemon = True
    th2.start()
except Exception as e:
    print(e)

try:
    server_HTTP2 = ThreadedHTTPServer((args.ip, HTTP_SERVER_PORT2), VideoStreamHandler)
    th3 = threading.Thread(target=server_HTTP2.serve_forever)
    th3.daemon = True
    th3.start()
except Exception as e:
    print(e)

try:
    server_HTTP3 = ThreadedHTTPServer((args.ip, HTTP_SERVER_PORT3), VideoStreamHandler)
    th4 = threading.Thread(target=server_HTTP3.serve_forever)
    th4.daemon = True
    th4.start()
except Exception as e:
    print(e)



# connect to device and start pipeline
with dai.Device(pipeline) as device:
    print(f"DepthAI running. Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT)}' for normal video stream.")
    print(f"Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT2)}' for warped video stream.")
    print(f"Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT3)}' for depth heatmap video stream.")
    print(f"Navigate to '{str(delta_host)}:{str(JSON_PORT)}' for detection data in json format.")

    # load transformation matrix
    with open("perspectiveCalibration/calibration_result", "rb") as ifile:
        transformation_matrix = pickle.load(ifile)

    # output queues will be used to get the rgb frames and nn data from the outputs defined above
    previewQueue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
    detectionNNQueue = device.getOutputQueue(name="detections", maxSize=4, blocking=False)
    depthQueue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
    networkQueue = device.getOutputQueue(name="nnNetwork", maxSize=4, blocking=False)

    startTime = time.monotonic()
    counter = 0
    fps = 0
    color = (255, 255, 255)

    while True:
        inPreview = previewQueue.get()
        inDet = detectionNNQueue.get()
        depth = depthQueue.get()
        inNN = networkQueue.get()

        frame = inPreview.getCvFrame()
        frame_copy = frame
        depthFrame = depth.getFrame()  # depthFrame values are in millimeters

        depth_downscaled = depthFrame[::4]
        min_depth = np.percentile(depth_downscaled[depth_downscaled != 0], 1)
        max_depth = np.percentile(depth_downscaled, 99)
        depthFrameColor = np.interp(depthFrame, (min_depth, max_depth), (0, 255)).astype(np.uint8)
        depthFrameColor = cv2.applyColorMap(depthFrameColor, cv2.COLORMAP_HOT)

        counter += 1
        current_time = time.monotonic()
        if (current_time - startTime) > 1:
            fps = counter / (current_time - startTime)
            counter = 0
            startTime = current_time

        detections = inDet.detections

        # If the detections is available, draw bounding boxes on it and show the frame
        height = frame.shape[0]
        width = frame.shape[1]
        for detection in detections:
            roiData = detection.boundingBoxMapping
            roi = roiData.roi
            roi = roi.denormalize(depthFrameColor.shape[1], depthFrameColor.shape[0])
            topLeft = roi.topLeft()
            bottomRight = roi.bottomRight()
            xmin = int(topLeft.x)
            ymin = int(topLeft.y)
            xmax = int(bottomRight.x)
            ymax = int(bottomRight.y)
            cv2.rectangle(depthFrameColor, (xmin, ymin), (xmax, ymax), color, 1)

            # Denormalize bounding box
            x1 = int(detection.xmin * width)
            x2 = int(detection.xmax * width)
            y1 = int(detection.ymin * height)
            y2 = int(detection.ymax * height)

            try:
                label = labels[detection.label]
            except:
                label = detection.label

            cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, "{:.2f}".format(detection.confidence * 100), (x1 + 10, y1 + 35),
                        cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, f"X: {int(detection.spatialCoordinates.x)} mm", (x1 + 10, y1 + 50),
                        cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, f"Y: {int(detection.spatialCoordinates.y)} mm", (x1 + 10, y1 + 65),
                        cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, f"Z: {int(detection.spatialCoordinates.z)} mm", (x1 + 10, y1 + 80),
                        cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

        # transform frame with perspective calibration
        if transformation_matrix.any():
            transformed_frame = cv2.warpPerspective(frame_copy, transformation_matrix, (width, height))
        else:
            transformed_frame = frame_copy

        # send frames using http servers
        server_HTTP.frametosend = frame
        server_HTTP2.frametosend = transformed_frame
        server_HTTP3.frametosend = depthFrameColor

        if preview:
            cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)
            cv2.imshow("depth", depthFrameColor)
            cv2.imshow("rgb", frame)

        if cv2.waitKey(1) == ord('q'):
            break