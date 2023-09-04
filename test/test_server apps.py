import json
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
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

# get user local IP to host over LAN the video, note the json file will be hosted over localhost
hostname = socket.gethostname()
IPAddress = socket.gethostbyname(hostname)

# parsing
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="Choose host: \n"
                                     "0 - delta simulation\n"
                                     "1 - real delta",
                    type=int, choices=[0, 1], default=0)
parser.add_argument("--ip", help="Set http and json servers ip-s. The default ip would be localhost",
                    type=str, default='localhost')

args = parser.parse_args()

# PORTS
HTTP_SERVER_PORT = 8090
HTTP_SERVER_PORT2 = 8080
JSON_PORT = 8070

if args.device == 0:
    delta_host, delta_port = "127.0.0.1", 2137
else:
    delta_host, delta_port = "192.168.0.155", 10


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
    daemon_threads = True


# enables to stream into two different ports
# def serve_forever(server1, server2, server3):
#     while True:
#         r, w, e = select.select([server1, server2, server3], [], [], 0)
#         if server1 in r:
#             server1.handle_request()
#         if server2 in r:
#             server2.handle_request()
#         if server3 in r:
#             server3.handle_request()





# # start TCP data server (JSON)
# try:
#     server_TCP = socketserver.TCPServer(("127.0.0.1", JSON_PORT), TCPServerRequest)
# except Exception as e:
#     print(e)
#
# th = threading.Thread(target=server_TCP.serve_forever)
# th.daemon = True
# th.start()

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
    server_HTTP3 = ThreadedHTTPServer((args.ip, 8060), VideoStreamHandler)
except Exception as e:
    print(e)

th4 = threading.Thread(target=server_HTTP3.serve_forever)
th4.daemon = True
th4.start()

vid = cv2.VideoCapture(0)

while True:
    ret, frame = vid.read()

    cv2.imshow('frame', frame)

    server_HTTP.frametosend = frame
    server_HTTP2.frametosend = frame
    server_HTTP3.frametosend = frame

    if cv2.waitKey(1) == ord('q'):
        break

vid.release()
cv2.destroyAllWindows()