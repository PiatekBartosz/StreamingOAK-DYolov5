import json
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
import depthai as dai
import cv2
from PIL import Image
import blobconverter
from pathlib import Path
import numpy as np
import pickle
import select
import socket
import sys
import argparse
from helper import deltaCommuncation as dc

# get user local IP to host over LAN the video, note the json file will be hosted over localhost
hostname = socket.gethostname()
IPAddress = socket.gethostbyname(hostname)

# parsing
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="Choose delta simulation or real delta (default: simulation)",
                    type=int, choices=[0, 1], default=0)
parser.add_argument("--ip", help="Set http server ip-s sending (camera view)", type=str, default=IPAddress)
parser.add_argument("--vision_only", help="Set 1 for only vision system functionality.",
                    type=int, choices=[0, 1], default=0)

args = parser.parse_args()

# PORTS
HTTP_SERVER_PORT = 8090
HTTP_SERVER_PORT2 = 8080
JSON_PORT = 8070

# using simulation 0 or delta 1
if args.device == 0:
    delta_host, delta_port = "localhost", 2137
else:
    delta_host, delta_port = "localhost", 10  # todo change localhost for delta ip

class TCPServerRequest(socketserver.BaseRequestHandler):
    def handle(self):
        # first send HTTP header
        header = 'HTTP/1.0 200 OK\r\nServer: Mozarella/2.2\r\nAccept-Range: bytes\r\nConnection: close\r\nMax-Age: 0\r\nExpires: 0\r\nCache-Control: no-cache, private\r\nPragma: no-cache\r\nContent-Type: application/json\r\n\r\n'
        self.request.send(header.encode())
        while True:
            time.sleep(0.1)
            if hasattr(self.server, 'datatosend'):
                self.request.send(self.server.datatosend.encode() + '\r\n'.encode())


class VideoStreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=--jpgboundary')
        self.end_headers()
        while True:
            time.sleep(0.1)
            if hasattr(self.server, 'frametosend'):
                image = Image.fromarray(cv2.cvtColor(self.server.frametosend, cv2.COLOR_BGR2RGB))
                stream_file = BytesIO()
                image.save(stream_file, 'JPEG')
                self.wfile.write("--jpgboundary".encode())

                self.send_header('Content-type', 'image/jpeg')
                self.send_header('Content-length', str(stream_file.getbuffer().nbytes))
                self.end_headers()
                image.save(self.wfile, 'JPEG')


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    # Handle request in a separate thread
    pass


# enables to stream into two different ports
def serve_forever(server1, server2):
    while True:
        r, w, e = select.select([server1, server2], [], [], 0)
        if server1 in r:
            server1.handle_request()
        if server2 in r:
            server2.handle_request()


def decode_name(label_num):
    decode_labels = {0: "3-bit", 1: "Mars", 2: "Milkyway", 3: "Snickers"}
    return decode_labels[label_num]


# open perspective calibration matrix
with open("perspectiveCalibration/calibration_result", "rb") as infile:
    transform_matrix = pickle.load(infile)

# parse config
configPath = Path("json/result_new.json")
if not configPath.exists():
    raise ValueError("Path {} does not exist!".format(configPath))

with configPath.open() as f:
    config = json.load(f)
nnConfig = config.get("nn_config", {})

# parse input shape
if "input_size" in nnConfig:
    W, H = tuple(map(int, nnConfig.get("input_size").split('x')))

# extract metadata
metadata = nnConfig.get("NN_specific_metadata", {})
classes = metadata.get("classes", {})
coordinates = metadata.get("coordinates", {})
anchors = metadata.get("anchors", {})
anchorMasks = metadata.get("anchor_masks", {})
iouThreshold = metadata.get("iou_threshold", {})
confidenceThreshold = metadata.get("confidence_threshold", {})

print(metadata)

# parse labels
nnMappings = config.get("mappings", {})
labels = nnMappings.get("labels", {})

# get model path
nnPath = Path("best_openvino_2021.4_6shave.blob")
if not Path(nnPath).exists():
    print("No blob found at {}.".format(nnPath))

# sync outputs
syncNN = True

# Create pipeline
pipeline = dai.Pipeline()

# Define sources and outputs
camRgb = pipeline.create(dai.node.ColorCamera)
detectionNetwork = pipeline.create(dai.node.YoloDetectionNetwork)
xoutRgb = pipeline.create(dai.node.XLinkOut)
nnOut = pipeline.create(dai.node.XLinkOut)

xoutRgb.setStreamName("rgb")
nnOut.setStreamName("nn")

# Properties
camRgb.setPreviewSize(W, H)
camRgb.setResolution(dai.ColorCameraProperties.SensorResolution.THE_1080_P)
camRgb.setInterleaved(False)
camRgb.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
camRgb.setFps(40)

# Network specific settings
detectionNetwork.setConfidenceThreshold(confidenceThreshold)
detectionNetwork.setNumClasses(classes)
detectionNetwork.setCoordinateSize(coordinates)
detectionNetwork.setAnchors(anchors)
detectionNetwork.setAnchorMasks(anchorMasks)
detectionNetwork.setIouThreshold(iouThreshold)
detectionNetwork.setBlobPath(nnPath)
detectionNetwork.setNumInferenceThreads(2)
detectionNetwork.input.setBlocking(False)

# Linking
camRgb.preview.link(detectionNetwork.input)
detectionNetwork.passthrough.link(xoutRgb.input)
detectionNetwork.out.link(nnOut.input)

# start TCP data server (JSON)
try:
    server_TCP = socketserver.TCPServer(("localhost", JSON_PORT), TCPServerRequest)
except Exception as e:
    print(e)

th = threading.Thread(target=server_TCP.serve_forever)
th.daemon = True
th.start()

# start MJPEG HTTP Servers
try:
    server_HTTP = ThreadedHTTPServer((args.ip, HTTP_SERVER_PORT), VideoStreamHandler)
except Exception as e:
    print(e)

th2 = threading.Thread(target=server_HTTP.serve_forever)
th2.daemon = True
th2.start()

try:
    server_HTTP2 = ThreadedHTTPServer((args.ip, HTTP_SERVER_PORT2), VideoStreamHandler)
except Exception as e:
    print(e)

th3 = threading.Thread(target=server_HTTP2.serve_forever)
th3.daemon = True
th3.start()

try:
    dc.delta_sock=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except Exception as e:
    print(e)

th3 = threading.Thread(target=dc.vision_system_loop)
th3.daemon = True
th3.start()


# Connect to device and start pipeline
with dai.Device(pipeline) as device:
    print(f"DepthAI running. Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT)}' for normal video stream.")
    print(f"Navigate to '{str(IPAddress)}:{str(HTTP_SERVER_PORT2)}' for warped video stream.")
    print(f"Navigate to 'localhost:{str(JSON_PORT)}' for detection data in json format.")

    # Output queues will be used to get the rgb frames and nn data from the outputs defined above
    qRgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)
    qDet = device.getOutputQueue(name="nn", maxSize=4, blocking=False)

    frame = None
    detections = []

    startTime = time.monotonic()
    counter = 0
    fps = 0
    color = (255, 255, 255)

    while True:
        inPreview = qRgb.get()
        frame = inPreview.getCvFrame()

        inNN = qDet.get()
        detections = inNN.detections

        counter += 1
        current_time = time.monotonic()
        if (current_time - startTime) > 1:
            fps = counter / (current_time - startTime)
            counter = 0
            startTime = current_time

        # if the frame is available, draw bbox-es on it and show
        height = frame.shape[0]
        width = frame.shape[1]

        send = {"3-bit": [], "Mars": [], "Milkyway": [], "Snickers": []}

        for detection in detections:

            # Denormalize bounding box
            x1 = int(detection.xmin * width)
            x2 = int(detection.xmax * width)
            y1 = int(detection.ymin * height)
            y2 = int(detection.ymax * height)

            # bbox middle coordinates
            bbox_x, bbox_y = int((x1 + x2) // 2), int((y1 + y2) // 2)
            if transform_matrix.any():
                # if perspective calibration was done calculate detection (x,y) on warped img
                t_bbox_x, t_bbox_y, scale = np.matmul(transform_matrix, np.float32([bbox_x, bbox_y, 1]))
                t_bbox_x, t_bbox_y = int(t_bbox_x / scale), int(t_bbox_y / scale)
            else:
                t_bbox_x, t_bbox_y = 0, 0

            label = decode_name(detection.label)
            cv2.putText(frame, str(label), (x1 + 10, y1 + 20), cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.putText(frame, "{:.2f}".format(detection.confidence * 100), (x1 + 10, y1 + 35),
                        cv2.FONT_HERSHEY_TRIPLEX, 0.5, color)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, cv2.FONT_HERSHEY_SIMPLEX)

            # todo offset the middle_transformed by half of the calibration square
            # prepare json file to send with TCP
            dim = {"xmax": detection.xmax, "xmin": detection.xmin, "ymax": detection.ymax, "ymin": detection.ymin,
                   "middle": (bbox_x, bbox_y), "middle_transformed": (t_bbox_x, t_bbox_y)}
            send[label].append(dim)

        # send json format detection with information about message size
        json_send = json.dumps(send)
        server_TCP.datatosend = json_send

        # send normal view camera
        cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)
        frame_cpy = frame
        cv2.imshow("frame", frame)
        server_HTTP.frametosend = frame

        # send birdview camera if perspective calibration was done
        if transform_matrix.any():
            # transform frame
            transformed_frame = cv2.warpPerspective(frame_cpy, transform_matrix, (W, H))

            # draw circle for every bar recognized in new perspective
            for choclate_bar_name in send:
                for detected_bar in send[choclate_bar_name]:
                    coordinates = detected_bar["middle_transformed"]
                    cv2.circle(transformed_frame, coordinates, 5, (255, 255, 255), -1)

            cv2.imshow("Transformed frame", transformed_frame)
            server_HTTP2.frametosend = transformed_frame

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
