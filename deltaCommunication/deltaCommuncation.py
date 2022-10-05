import socket
from threading import Thread

HOST, PORT = "localhost", 2137

# parse x, y, z position from robot callback
def get_pos(s):
    x = int(s[3:7])
    y = int(s[8:12])
    z = int(s[13:17])
    return x, y, z

def handle_communication():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        # set start position
        sock.sendall(bytes("LIN+4500+0000+0000TOOL", "utf-8"))
        sock.sendall(bytes("G_P", "utf-8"))
        recv = str(sock.recv(1024), "utf-8")
        print(recv)
        print(get_pos(recv))
        # while 1:
        #     if queue:



thread1 = Thread(target=handle_communication)
thread1.start()
thread1.join()
queue = [(2500, 5300), (2444, 2555)]


