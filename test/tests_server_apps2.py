import cv2
import http.server
import socketserver
import threading
import io
import numpy as np
from PIL import Image

class VideoStreamHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video_feed':
            # Set the response header to indicate that we're sending a multipart content
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()

            # Capture video from the webcam
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                self.send_error(500, 'Failed to access the webcam.')
                return

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break

                    # Convert the frame to a format suitable for HTTP response (JPEG)
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_pil = Image.fromarray(frame)
                    img_byte_array = io.BytesIO()
                    frame_pil.save(img_byte_array, format='JPEG')
                    frame_bytes = img_byte_array.getvalue()

                    # Send the frame as a multipart response to the client
                    self.send_frame(frame_bytes)

            except Exception as e:
                print("Error:", e)

            finally:
                cap.release()

    def send_frame(self, frame_bytes):
        self.wfile.write(b'--frame\r\n')
        self.send_header('Content-type', 'image/jpeg')
        self.send_header('Content-length', len(frame_bytes))
        self.end_headers()
        self.wfile.write(frame_bytes)
        self.wfile.write(b'\r\n')

def run_server(port):
    try:
        server_address = ('localhost', port)
        httpd = socketserver.TCPServer(server_address, VideoStreamHandler)
        print(f"Server started on port {port}")
        httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"Server on port {port} is shutting down...")
        httpd.server_close()

if __name__ == "__main__":
    port_number = 8000  # Change this to your desired port number

    # Create and start the server in a separate thread
    server_thread = threading.Thread(target=run_server, args=(port_number,))
    server_thread.daemon = True
    server_thread.start()

    try:
        # Keep the main thread running until interrupted (e.g., Ctrl+C)
        while True:
            pass
    except KeyboardInterrupt:
        print("Main thread is shutting down...")
