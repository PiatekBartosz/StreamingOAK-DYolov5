import socket
from threading import Thread
import logging

HOST, PORT = "localhost", 2137
obj_hover_height = "+4000"
obj_pickup_height = "+0000"
error = 100 # how much can differ the real and set position
queue = [(2500, 5300, 0), (2444, 2555, 1)] # later will be replaced with vision system return (x, y, type)

# put down location coordinates in string format
put1 = "+1000+1000"
put2 = "+1000-1000"
put3 = "-1000+1000"
put4 = "-1000-1000"

def handle_communication():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        # set start position
        sock.sendall(bytes("LIN+4500+0000+0000TOOL", "utf-8"))
        sock.sendall(bytes("G_P", "utf-8"))
        recv = str(sock.recv(1024), "utf-8")
        print("test")
        logging.info(recv)
        logging.info(get_pos(recv))
            # while 1:
            #     if queue:

# parse x, y, z position from robot callback
def get_coordinates(s):
    x = int(s[4:7]) if s[3] == "+" else int(s[4:7]) * (-1)
    y = int(s[8:11]) if s[3] == "+" else int(s[8:11]) * (-1)
    z = int(s[12:15]) if s[3] == "+" else int(s[12:15]) * (-1)
    # todo convert to number normalize x, y, z and convert back to string
    return x, y, z

# creates series of commands that create a trajectory for the robot to pick object
def pick_up_obj(x, y):
    commands = create_commands(x, y)
    return None

def wait_unitl_achieved_pos(x_set, y_set, sock):
    sock.send(bytes("G_P", "utf-8"))
    recv = sock.recv(str(sock.recv(1024), "utf-8"))
    x_curr, y_curr, z_curr = get_coordinates(recv)

    while x_curr-x_set > error or y_curr-y_set > error or z_curr-z_set > error:
        sock.send(bytes("G_P", "utf-8"))
        recv = sock.recv(str(sock.recv(1024), "utf-8"))
        x_curr, y_curr, z_curr = get_coordinates(recv)

def create_commands(x, y, type):
    commands = []

    x = "+" + str(x) if x >= 0 else str(x)
    y = "+" + str(x) if y >= 0 else str(y)

    # hover over object to pickup
    commands.extend(x+y)

    # put down to specific location and go to default position
    match type:
        case 1:
            commands.extend(put1)
        case 2:
            commands.extend(put2)
        case 3:
            commands.extend(put3)
        case 4:
            commands.extend(put4)
    return commands


def pick_up_command(coordinates):
    pick_up = []
    pick_up.append("LIN" + coordinates + obj_pickup_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_pickup_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_pickup_height + "TOOL")
    return pick_up

thread1 = Thread(target=handle_communication)
thread1.daemon == True
thread1.start()
thread1.join()



