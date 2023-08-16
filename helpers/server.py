import socketserver
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from PIL import Image
import cv2
from io import BytesIO
import select


def serve_forever(server1, server2, server3):
    # it is required to run multiple servers using http.server in parallel
    while True:
        r, w, e = select.select([server1, server2, server3], [], [], 0)
        if server1 in r:
            server1.handle_request()
        if server2 in r:
            server2.handle_request()
        if server3 in r:
            server3.handle_request()


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



