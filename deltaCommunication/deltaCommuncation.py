import socket
from threading import Thread
from time import sleep

HOST, PORT = "localhost", 2137
obj_hover_height = "+4000"
obj_pickup_height = "+0000"
error = 100  # how much can differ the real and set position
queue = [(2500, 5300, 0), (2444, 2555, 1)]  # later will be replaced with vision system return (x, y, type_of)

# put down location coordinates in string format
put_location_1 = "+1000+1000"
put_location_2 = "+1000-1000"
put_location_3 = "-1000+1000"
put_location_4 = "-1000-1000"

def handle_communication():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((HOST, PORT))

        # set start position
        sock.sendall(bytes("LIN+4500+0000+0000TOOL", "utf-8"))
        sock.sendall(bytes("G_P", "utf-8"))
        recv = str(sock.recv(1024), "utf-8")
        print("Current position: ", get_coordinates(recv))
        while queue:
            pick_up_obj(queue[0][0], queue[0][1], queue[0][2], sock)
            queue.pop(-1)
        print("end")


# parse x, y, z position from robot callback
def get_coordinates(s):
    x = int(s[4:8]) if s[3] == "+" else int(s[3:8]) * (-1)
    y = int(s[9:13]) if s[8] == "+" else int(s[8:13]) * (-1)
    z = int(s[14:18]) if s[13] == "+" else int(s[13:18]) * (-1)
    # todo convert to number normalize x, y, z and convert back to string
    return x, y, z


# creates series of commands that create a trajectory for the robot to pick object
def pick_up_obj(x, y, type_of, sock):
    commands = create_commands(x, y, type_of)
    while commands:
        x_set, y_set, z_set = get_coordinates(commands[0])
        sock.sendall(commands[0])
        wait_unitl_achieved_pos(x_set, y_set, z_set, sock)
        commands.pop(0)

def create_commands(x, y, type_of):
    commands = []

    x = "+" + str(x) if x >= 0 else str(x)
    y = "+" + str(y) if y >= 0 else str(y)

    # pick up object
    commands.extend(pick_up_command(x+y))

    # put down to specific location and go to default position
    match type_of:
        case 0:
            commands.extend(putting_down_command(put_location_1))
        case 1:
            commands.extend(putting_down_command(put_location_2))
        case 2:
            commands.extend(putting_down_command(put_location_3))
        case 3:
            commands.extend(putting_down_command(put_location_4))

    # return home command
    commands.append("LIN+4500+0000+0000TOOL")
    return commands


# todo update to enable controlling the suction cup and differentiate between picking up and putting down
def pick_up_command(coordinates):
    pick_up = []
    pick_up.append("LIN" + coordinates + obj_hover_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_pickup_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_hover_height + "TOOL")
    return pick_up


def putting_down_command(put_location):
    put_down = []
    put_down.append("LIN" + put_location + obj_hover_height + "TOOL")
    put_down.append("LIN" + put_location + obj_pickup_height + "TOOL")
    put_down.append("LIN" + put_location + obj_hover_height + "TOOL")
    return put_down

def wait_unitl_achieved_pos(x_set, y_set, z_set, sock):
    sock.send(bytes("G_P", "utf-8"))
    recv = sock.recv(str(sock.recv(1024), "utf-8"))
    x_curr, y_curr, z_curr = get_coordinates(recv)

    while x_curr-x_set > error or y_curr-y_set > error or z_curr-z_set > error:
        sock.send(bytes("G_P", "utf-8"))
        recv = sock.recv(str(sock.recv(1024), "utf-8"))
        if recv:
            x_curr, y_curr, z_curr = get_coordinates(recv)
        sleep(100)


thread1 = Thread(target=handle_communication)
thread1.daemon == True
thread1.start()



