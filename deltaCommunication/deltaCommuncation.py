import socket
from threading import Thread
from time import sleep

HOST, PORT = "localhost", 2137
home_pos = "-2000-2000-4500"
obj_hover_height = "-4500"
obj_pickup_height = "-7000"
error = 100  # how much can differ the real and set position
queue = [(2500, 5300, 0), (2444, 2555, 1)]  # later will be replaced with vision system return (x, y, type_of)

# put down location coordinates
put_location_1 = "+1000+1000"
put_location_2 = "+1000-1000"
put_location_3 = "-1000+1000"
put_location_4 = "-1000-1000"

global sock
global current_position
global running
running = True


def handle_communication():
    while queue:
        x, y, type_of = queue[0][0], queue[0][1], queue[0][2]
        commands = create_commands(x, y, type_of)

        while commands:
            x_set, y_set, z_set = get_coordinates(commands[0])
            sock.send(bytes(commands[0], "utf-8"))
            wait_until_achieved_pos(x_set, y_set, z_set)
            commands.pop(0)
        queue.pop(-1)
        print("end")
    running = False


def get_pos():
    while running:
        sock.send(bytes("G_P", "utf-8"))
        recv = get_coordinates(sock.recv(128), "utf-8")
        current_position = recv
        sleep(0.03)


def get_coordinates(s):
    x = int(s[4:8]) if s[3] == "+" else int(s[3:8])
    y = int(s[9:13]) if s[8] == "+" else int(s[8:13])
    z = int(s[14:18]) if s[13] == "+" else int(s[13:18])
    # todo convert to number normalize x, y, z
    return x, y, z
# parse x, y, z position from robot callbackz


def create_commands(x, y, type_of):
    commands = []

    x = "+" + str(x) if x >= 0 else str(x)
    y = "+" + str(y) if y >= 0 else str(y)

    # pick up object
    commands.extend(pick_up_command(x + y))

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
    commands.append("LIN" + home_pos + "TOOL")
    return commands


def pick_up_command(coordinates):
    pick_up = []
    pick_up.append("LIN" + coordinates + obj_hover_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_pickup_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_hover_height + "TOOL")
    return pick_up
# todo update to enable controlling the suction cup and differentiate between picking up and putting down


def putting_down_command(put_location):
    put_down = []
    put_down.append("LIN" + put_location + obj_hover_height + "TOOL")
    put_down.append("LIN" + put_location + obj_pickup_height + "TOOL")
    put_down.append("LIN" + put_location + obj_hover_height + "TOOL")
    return put_down


def wait_until_achieved_pos(x_set, y_set, z_set):
    x_curr, y_curr, z_curr = current_position
    while abs(x_curr - x_set) > error or abs(y_curr - y_set) > error or abs(z_curr - z_set) > error:
        x_curr, y_curr, z_curr = current_position
        sleep(0.01)
    return


#
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

print("Connected to delta")

# set home position
sock.sendall(bytes("LIN" + home_pos + "TOOL", "utf-8"))

# init current position
sock.sendall(bytes("G_P", "utf-8"))
recv = str(sock.recv(128), "utf-8")
current_position = get_coordinates(recv)

# thread1 = Thread(target=handle_communication)
thread2 = Thread(target=get_pos)

# thread1.start()
thread2.start()

