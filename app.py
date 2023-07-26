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
import re
from helpers.server import TCPServerRequest, VideoStreamHandler, ThreadedHTTPServer, serve_forever
from helpers.delta import RobotDeltaClient


class DeltaRobotClient:
    def __init__(self):
        pass

class DepthAiApp:
    def __init__(self, args):
        self.server_TCP = None
        self.server_HTTP = None
        self.server_HTTP2 = None
        self.server_HTTP3 = None
        self.args = args
        self.pipeline = dai.Pipeline()
        self.server_TCP_thread = None
        self.server_HTTP_thread = None
        self.server_HTTP_thread_2 = None
        self.server_HTTP_thread_3 = None
        self.delta_client = None
        self.threads = []
        self.labels = []
        self.detections = []
        self.depth_bool = bool(self.args.depth)
        self.preview_bool = bool(self.args.preview)
        self.sort_bool = bool(self.args.sort)
        self.IPAddress = args.ip
        self.transformation_matrix = None

        # parse args
        if self.args.device == 0:
            self.delta_host, self.delta_port = "127.0.0.1", 2137
        else:
            self.delta_host, self.delta_port = "192.168.0.155", 10

        # PORTS
        self.HTTP_SERVER_PORT = 8090
        self.HTTP_SERVER_PORT2 = 8080
        if self.depth_bool:
            self.HTTP_SERVER_PORT3 = 8070
        self.JSON_PORT = 8060

    def setup_pipeline(self):
        # load transformation matrix
        if self.depth_bool:
            # load transformation matrix
            with open("perspectiveCalibration/calibration_result", "rb") as ifile:
                self.transformation_matrix = pickle.load(ifile)

            """
                 Define pipeline & nodes
            """

            if self.depth_bool:
                camRgb = self.pipeline.create(dai.node.ColorCamera)
                detectionNetwork = self.pipeline.create(dai.node.YoloSpatialDetectionNetwork)
                monoLeft = self.pipeline.create(dai.node.MonoCamera)
                monoRight = self.pipeline.create(dai.node.MonoCamera)
                stereo = self.pipeline.create(dai.node.StereoDepth)
            else:
                camRgb = self.pipeline.create(dai.node.ColorCamera)
                detectionNetwork = self.pipeline.create(dai.node.YoloDetectionNetwork)

            # outputs nodes
            if self.depth_bool:
                nnNetworkOut = self.pipeline.create(dai.node.XLinkOut)
                xoutNN = self.pipeline.create(dai.node.XLinkOut)
                xoutRgb = self.pipeline.create(dai.node.XLinkOut)
                xoutDepth = self.pipeline.create(dai.node.XLinkOut)

                xoutRgb.setStreamName("rgb")
                xoutNN.setStreamName("detections")
                nnNetworkOut.setStreamName("nnNetwork")
                xoutDepth.setStreamName("depth")
            else:
                xoutNN = self.pipeline.create(dai.node.XLinkOut)
                xoutRgb = self.pipeline.create(dai.node.XLinkOut)

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

            if self.depth_bool:
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

            if self.depth_bool:
                # spatial Yolo detection parameters
                detectionNetwork.input.setBlocking(False)
                detectionNetwork.setBoundingBoxScaleFactor(0.5)
                detectionNetwork.setDepthLowerThreshold(100)  # Min 10 centimeters
                detectionNetwork.setDepthUpperThreshold(5000)  # Max 5 meters

            # configure Yolo
            detectionNetwork.setNumClasses(nnConfig["NN_specific_metadata"]["classes"])
            detectionNetwork.setCoordinateSize(nnConfig["NN_specific_metadata"]["coordinates"])
            detectionNetwork.setAnchors(nnConfig["NN_specific_metadata"]["anchors"])
            detectionNetwork.setAnchorMasks(nnConfig["NN_specific_metadata"]["anchor_masks"])
            detectionNetwork.setIouThreshold(nnConfig["NN_specific_metadata"]["iou_threshold"])
            detectionNetwork.setConfidenceThreshold(nnConfig["NN_specific_metadata"]["confidence_threshold"])

            # get labels
            self.labels = config["mappings"]["labels"]

            """
                Link pipeline nodes
            """
            if self.depth_bool:
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


    def start_servers(self):
        """
            Start servers
        """

        # start TCP data server (JSON)
        try:
            self.server_TCP = socketserver.TCPServer((self.args.ip, self.JSON_PORT), TCPServerRequest)

        except Exception as e:
            print(e)

        self.server_TCP_thread = threading.Thread(target=self.server_TCP.serve_forever)
        self.server_TCP_thread.daemon = True
        self.server_TCP_thread.start()

        # start MJPEG HTTP Servers
        try:
            self.server_HTTP = ThreadedHTTPServer((self.args.ip, self.HTTP_SERVER_PORT), VideoStreamHandler)
        except Exception as e:
            print(e)

        self.server_HTTP_thread = threading.Thread(target=self.server_HTTP.serve_forever)
        self.server_HTTP_thread.daemon = True
        self.server_HTTP_thread.start()

        try:
            self.server_HTTP2 = ThreadedHTTPServer((self.args.ip, self.HTTP_SERVER_PORT2), VideoStreamHandler)
        except Exception as e:
            print(e)

        self.server_HTTP_thread_2 = threading.Thread(target=self.server_HTTP2.serve_forever)
        self.server_HTTP_thread_2.daemon = True
        self.server_HTTP_thread_2.start()

        if self.depth_bool:
            try:
                self.server_HTTP3 = ThreadedHTTPServer((self.args.ip, self.HTTP_SERVER_PORT3), VideoStreamHandler)
            except Exception as e:
                print(e)

            self.server_HTTP_thread_3 = threading.Thread(target=self.server_HTTP3.serve_forever)
            self.server_HTTP_thread_3.daemon = True
            self.server_HTTP_thread_3.start()

        # if self.sort_bool:
        #     try:
        #         delta_client = RobotDeltaClient(self.delta_host, self.delta_port)
        #         self.delta_client = threading.Thread(target=delta_client.handle_communication)
        #     except Exception as e:
        #         print(e)


    def run(self):
        self.setup_pipeline()
        with dai.Device(self.pipeline) as device:
            print("DepthAI running.")
            print(f"Navigate to '{str(self.IPAddress)}:{str(self.HTTP_SERVER_PORT)}' for normal video stream.")
            print(f"Navigate to '{str(self.IPAddress)}:{str(self.HTTP_SERVER_PORT2)}' for warped video stream.")
            if self.depth_bool:
                print(f"Navigate to '{str(self.IPAddress)}:{str(self.HTTP_SERVER_PORT3)}' for depth heatmap video stream.")
            print(f"Navigate to '{str(self.IPAddress)}:{str(self.JSON_PORT)}' for detection data in json format.")



            if self.depth_bool:
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
                if self.depth_bool:
                    inDepth = depthQueue.get()
                    inNN = networkQueue.get()

                frame = inPreview.getCvFrame()
                frame_copy = frame
                if self.depth_bool:
                    depthFrame = inDepth.getFrame()  # depthFrame values are in millimeters
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

                self.detections = inDet.detections

                # If the detections is available, draw bounding boxes on it and show the frame
                height = frame.shape[0]
                width = frame.shape[1]

                # prepare dictionary for json format send
                send = {el: [] for el in self.labels}

                for detection in self.detections:

                    # Denormalize bounding box
                    x1 = int(detection.xmin * width)
                    x2 = int(detection.xmax * width)
                    y1 = int(detection.ymin * height)
                    y2 = int(detection.ymax * height)

                    try:
                        label = self.labels[detection.label]
                    except:
                        label = detection.label

                    # bbox middle coordinates
                    bbox_x, bbox_y = int((x1 + x2) // 2), int((y1 + y2) // 2)
                    if self.transformation_matrix.any():
                        # if perspective calibration was done calculate detection (x,y) on warped img
                        t_bbox_x, t_bbox_y, scale = np.matmul(self.transformation_matrix, np.float32([bbox_x, bbox_y, 1]))
                        t_bbox_x, t_bbox_y = int(t_bbox_x / scale), int(t_bbox_y / scale)
                    else:
                        t_bbox_x, t_bbox_y = None, None

                    if self.depth_bool:
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
                    if self.depth_bool:
                        spatialXYZ = (detection.spatialCoordinates.x, detection.spatialCoordinates.y,
                                      detection.spatialCoordinates.z)
                    else:
                        spatialXYZ = (None, None, None)

                    det = {"x_max": detection.xmax, "x_min": detection.xmin, "y_max": detection.ymax,
                           "y_min": detection.ymin,
                           "middle": (bbox_x, bbox_y), "middle_transformed": (t_bbox_x, t_bbox_y),
                           "conf": detection.confidence,
                           "spatial_xyz": spatialXYZ}
                    send[label].append(det)

                # send birdview camera if perspective calibration was done
                if self.transformation_matrix.any():

                    # transform frame
                    transformed_frame = cv2.warpPerspective(frame_copy, self.transformation_matrix, (width, height))

                    # draw circle for every bar recognized in new perspective
                    for choclate_bar_name in send:
                        for detected_bar in send[choclate_bar_name]:
                            coordinates = detected_bar["middle_transformed"]
                            cv2.circle(transformed_frame, coordinates, 5, (255, 255, 255), -1)
                    self.server_HTTP2.frametosend = transformed_frame

                # encode json file and send it using TCP
                json_send = json.dumps(send)
                self.server_TCP.datatosend = json_send

                # send frames using http servers
                self.server_HTTP.frametosend = frame
                if self.depth_bool:
                    self.server_HTTP3.frametosend = depthFrameColor

                if self.preview_bool:
                    cv2.putText(frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4), cv2.FONT_HERSHEY_TRIPLEX,
                                0.4, color)
                    cv2.putText(transformed_frame, "NN fps: {:.2f}".format(fps), (2, frame.shape[0] - 4),
                                cv2.FONT_HERSHEY_TRIPLEX, 0.4, color)

                    cv2.imshow("rgb", frame)
                    cv2.imshow("Transformed frame", transformed_frame)

                    if self.depth_bool:
                        cv2.imshow("depth", depthFrameColor)

                if cv2.waitKey(1) == ord('q'):
                    break



if __name__ == "__main__":
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
    parser.add_argument("-s", "--sort", help="Enables automatic sorting: \n0 - sorting off\n1 - sorting on",
                        type=int, choices=[0, 1], default=1)

    args = parser.parse_args()

    app = DepthAiApp(args)
    app.start_servers()
    app.run()






