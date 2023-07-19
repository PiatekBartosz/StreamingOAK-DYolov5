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
parser.add_argument("-D", "--depth", help="Choose depth: \n0 - depth off\n1 - depth on",
                    type=int, choices=[0, 1], default=1)

args = parser.parse_args()

if args.device == 0:
    delta_host, delta_port = "127.0.0.1", 2137
else:
    delta_host, delta_port = "192.168.0.155", 10

IPAddress = args.ip

if args.preview:
    previewBool = True
else:
    previewBool = False

if args.depth:
    depthBool = True
else:
    depthBool = False

# PORTS
HTTP_SERVER_PORT = 8090
HTTP_SERVER_PORT2 = 8080
if depthBool:
    HTTP_SERVER_PORT3 = 8070
JSON_PORT = 8060

"""
    Define pipeline & nodes
"""

pipeline = dai.Pipeline()

if depthBool:
    camRgb = pipeline.create(dai.node.ColorCamera)
    detectionNetwork = pipeline.create(dai.node.YoloSpatialDetectionNetwork)
    monoLeft = pipeline.create(dai.node.MonoCamera)
    monoRight = pipeline.create(dai.node.MonoCamera)
    stereo = pipeline.create(dai.node.StereoDepth)
else:
    camRgb = pipeline.create(dai.node.ColorCamera)
    detectionNetwork = pipeline.create(dai.node.YoloDetectionNetwork)

# outputs nodes
if depthBool:
    nnNetworkOut = pipeline.create(dai.node.XLinkOut)
    xoutNN = pipeline.create(dai.node.XLinkOut)
    xoutRgb = pipeline.create(dai.node.XLinkOut)
    xoutDepth = pipeline.create(dai.node.XLinkOut)

    xoutRgb.setStreamName("rgb")
    xoutNN.setStreamName("detections")
    nnNetworkOut.setStreamName("nnNetwork")
    xoutDepth.setStreamName("depth")
else:
    xoutNN = pipeline.create(dai.node.XLinkOut)
    xoutRgb = pipeline.create(dai.node.XLinkOut)

    xoutRgb.setStreamName("rgb")
    xoutNN.setStreamName("detections")

"""
    Define pipeline nodes properties
"""

# nodes properties
camRgb.setPreviewSize(416, 416)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
camRgb.setInterleaved(False)
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
camRgb.setFps(40)

if depthBool:
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
detectionNetwork.setBlobPath(Path("config/yoloModel.blob"))

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

if depthBool:
    # spatial Yolo detection parameters
    detectionNetwork.input.setBlocking(False)
    detectionNetwork.setBoundingBoxScaleFactor(0.5)
    detectionNetwork.setDepthLowerThreshold(100) # Min 10 centimeters
    detectionNetwork.setDepthUpperThreshold(5000) # Max 5 meters

# configure Yolo
detectionNetwork.setNumClasses(nnConfig["NN_specific_metadata"]["classes"])
detectionNetwork.setCoordinateSize(nnConfig["NN_specific_metadata"]["coordinates"])
detectionNetwork.setAnchors(nnConfig["NN_specific_metadata"]["anchors"])
detectionNetwork.setAnchorMasks(nnConfig["NN_specific_metadata"]["anchor_masks"])
detectionNetwork.setIouThreshold(nnConfig["NN_specific_metadata"]["iou_threshold"])
detectionNetwork.setConfidenceThreshold(nnConfig["NN_specific_metadata"]["confidence_threshold"])

# get labels
labels = config["mappings"]["labels"]

"""
    Link pipeline nodes
"""
if depthBool:
    monoLeft.out.link(stereo.left)
    monoRight.out.link(stereo.right)

    stereo.depth.link(detectionNetwork.inputDepth)

    camRgb.preview.link(detectionNetwork.input)

    detectionNetwork.passthrough.link(xoutRgb.input)  # TODO should be sync with detection ?
    detectionNetwork.passthroughDepth.link(xoutDepth.input)
    detectionNetwork.outNetwork.link(nnNetworkOut.input)
    detectionNetwork.out.link(xoutNN.input)

else:
    camRgb.preview.link(detectionNetwork.input)
    detectionNetwork.passthrough.link(xoutRgb.input)
    detectionNetwork.out.link(xoutNN.input)

"""
    Start servers
"""

# start TCP data server (JSON)
try:
    server_TCP = socketserver.TCPServer(("127.0.0.1", JSON_PORT), TCPServerRequest)
    th = threading.Thread(target=server_TCP.serve_forever)
    th.daemon = True
    th.start()
except Exception as e:
    print(e)

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

if depthBool:
    try:
        server_HTTP3 = ThreadedHTTPServer((args.ip, HTTP_SERVER_PORT3), VideoStreamHandler)
        th4 = threading.Thread(target=server_HTTP3.serve_forever)
        th4.daemon = True
        th4.start()
    except Exception as e:
        print(e)


# connect to device and start pipeline
with dai.Device(pipeline) as device:
    print("DepthAI running.")
    print(f"Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT)}' for normal video stream.")
    print(f"Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT2)}' for warped video stream.")
    if depthBool:
        print(f"Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT3)}' for depth heatmap video stream.")
    print(f"Navigate to '{str(IPAddress)}:{str(JSON_PORT)}' for detection data in json format.")

    # load transformation matrix
    with open("perspectiveCalibration/calibration_result", "rb") as ifile:
        transformation_matrix = pickle.load(ifile)

    if depthBool:
        # output queues will be used to get the rgb frames and nn data from the outputs defined above
        previewQueue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        detectionNNQueue = device.getOutputQueue(name="detections", maxSize=4, blocking=False)
        depthQueue = device.getOutputQueue(name="depth", maxSize=4, blocking=False)
        networkQueue = device.getOutputQueue(name="nnNetwork", maxSize=4, blocking=False)
    else:
        previewQueue = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
        detectionNNQueue = device.getOutputQueue(name="detections", maxSize=4, blocking=False)

    startTime = time.monotonic()
    counter = 0
    fps = 0
    color = (255, 255, 255)

    while True:
        inPreview = previewQueue.get()
        inDet = detectionNNQueue.get()
        if depthBool:
            depthBool = depthQueue.get()
            inNN = networkQueue.get()

        frame = inPreview.getCvFrame()
        frame_copy = frame
        if depthBool:
            depthFrame = depthBool.getFrame()  # depthFrame values are in millimeters
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

        # prepare dictionary for json format send
        send = {el: [] for el in labels}

        for detection in detections:

            # TODO delete?
            # if depthBool:
            #     roiData = detection.boundingBoxMapping
            #     roi = roiData.roi
            #     roi = roi.denormalize(depthFrameColor.shape[1], depthFrameColor.shape[0])
            #     topLeft = roi.topLeft()
            #     bottomRight = roi.bottomRight()
            #     xmin = int(topLeft.x)
            #     ymin = int(topLeft.y)
            #     xmax = int(bottomRight.x)
            #     ymax = int(bottomRight.y)

            # Denormalize bounding box
            x1 = int(detection.xmin * width)
            x2 = int(detection.xmax * width)
            y1 = int(detection.ymin * height)
            y2 = int(detection.ymax * height)

            try:
                label = labels[detection.label]
            except:
                label = detection.label

            # bbox middle coordinates
            bbox_x, bbox_y = int((x1 + x2) // 2), int((y1 + y2) // 2)
            if transformation_matrix.any():
                # if perspective calibration was done calculate detection (x,y) on warped img
                t_bbox_x, t_bbox_y, scale = np.matmul(transformation_matrix, np.float32([bbox_x, bbox_y, 1]))
                t_bbox_x, t_bbox_y = int(t_bbox_x / scale), int(t_bbox_y / scale)
            else:
                t_bbox_x, t_bbox_y = None, None

            if depthBool:
                cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
                cv2.putText(frame, "{:.2f}".format(detection.confidence * 100), (x1 + 10, y1 + 35),
                            cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
                cv2.putText(frame, f"X: {int(detection.spatialCoordinates.x)} mm", (x1 + 10, y1 + 50),
                            cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
                cv2.putText(frame, f"Y: {int(detection.spatialCoordinates.y)} mm", (x1 + 10, y1 + 65),
                            cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
                cv2.putText(frame, f"Z: {int(detection.spatialCoordinates.z)} mm", (x1 + 10, y1 + 80),
                            cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)

            else:
                cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
                cv2.putText(frame, "{:.2f}".format(detection.confidence * 100), (x1 + 10, y1 + 35),
                            cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

            # append "send" json file
            if depthBool:
                spatialXYZ = (detection.spatialCoordinates.x, detection.spatialCoordinates.y,
                                   detection.spatialCoordinates.z)
            else:
                spatialXYZ = (None, None, None)

            det = {"x_max": detection.xmax, "x_min": detection.xmin, "y_max": detection.ymax, "y_min": detection.ymin,
                   "middle": (bbox_x, bbox_y), "middle_transformed": (t_bbox_x, t_bbox_y), "conf": detection.confidence,
                   "spatial_xyz": spatialXYZ}
            send[label].append(det)

        # send birdview camera if perspective calibration was done
        if transformation_matrix.any():

            # transform frame
            transformed_frame = cv2.warpPerspective(frame_copy, transformation_matrix, (width, height))

            # draw circle for every bar recognized in new perspective
            for choclate_bar_name in send:
                for detected_bar in send[choclate_bar_name]:
                    coordinates = detected_bar["middle_transformed"]
                    cv2.circle(transformed_frame, coordinates, 5, (255, 255, 255), -1)
            server_HTTP2.frametosend = transformed_frame

        # encode json file and send it using TCP
        json_send = json.dumps(send)
        server_TCP.datatosend = json_send

        # send frames using http servers
        server_HTTP.frametosend = frame
        if depthBool:
            server_HTTP3.frametosend = depthFrameColor

        if previewBool:
            cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)
            cv2.putText(transformed_frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)

            cv2.imshow("rgb", frame)
            cv2.imshow("Transformed frame", transformed_frame)

            if depthBool:
                cv2.imshow("depth", depthFrameColor)

        if cv2.waitKey(1) == ord('q'):
            break