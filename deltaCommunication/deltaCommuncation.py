import socket
from threading import Thread
from time import sleep

"""
    Boundaries for robot delta:
        z belongs to [-7000, -4000]
        for z == -4000 x and y belongs to [-3700, 3700]
        for z == -7000 x and y belongs to [-3000, 3000]
"""


HOST, PORT = "192.168.0.155", 10
home_pos = "-2000-2000-4500"
obj_hover_height = "-4500"
obj_pickup_height = "-7000"
offset_threshold = 100  # how much can differ the real and set position
sleep_time = 0.2  # how long in seconds will the G_P command be send while checking if achieved position
queue = [(2500, 1300, 0), (2444, 2555, 1), (2444, 2565, 3), (2444, -1500, 2)]  # later will be replaced with vision system return (x, y, type_of)

# put down location coordinates
put_location_1 = "+1000+1000"
put_location_2 = "+1000-1000"
put_location_3 = "-1000+1000"
put_location_4 = "-1000-1000"


def execute_command(command):
    return_value = None
    prefix = command[0:3]

    if prefix == "G_P":
        sock.send("G_P".encode())
        recv = sock.recv(26).decode()
        return recv

    elif prefix == "LIN":
        print("Performing: ", command)
        set_x, set_y, set_z = get_coordinates(command)
        sock.send(command.encode())
        sleep(sleep_time)
        while True:
            sock.send("G_P".encode())
            recv = sock.recv(26).decode()
            curr_x, curr_y, curr_z = get_coordinates(recv)
            print("Current position: ", curr_x, " ", curr_y, " ", curr_z, " ")

            offsets = []
            offsets.append(abs(set_x - curr_x))
            offsets.append(abs(set_y - curr_y))
            offsets.append(abs(set_z - curr_z))

            if max(offsets) <= offset_threshold:
                break
            else:
                sock.send(command.encode())
            sleep(sleep_time)

    elif prefix == "TIM":
        timeout = command[3:6]
        sleep(int(timeout)//1000)
    elif prefix == "JNT":
        pass

    elif prefix == "CIR":
        pass

    sleep(sleep_time)
    return


# todo update to enable controlling the suction cup and differentiate between picking up and putting down
def pick_up_command(coordinates):
    pick_up = []
    pick_up.append("LIN" + coordinates + obj_hover_height + "TOOL")
    pick_up.append("LIN" + coordinates + obj_pickup_height + "TOOL")
    pick_up.append("TIM" + str(2000))
    pick_up.append("LIN" + coordinates + obj_hover_height + "TOOL")
    return pick_up


def putting_down_command(put_location):
    put_down = []
    put_down.append("LIN" + put_location + obj_hover_height + "TOOL")
    put_down.append("LIN" + put_location + obj_pickup_height + "TOOL")
    put_down.append("TIM" + str(2000))
    put_down.append("LIN" + put_location + obj_hover_height + "TOOL")
    return put_down


def get_coordinates(s):
    x = int(s[4:8]) if s[3] == "+" else int(s[3:8])
    y = int(s[9:13]) if s[8] == "+" else int(s[8:13])
    z = int(s[14:18]) if s[13] == "+" else int(s[13:18])
    # todo convert to number normalize x, y, z
    return x, y, z


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


def start():
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    sleep(1)
    print("Connected to delta")

    # go home
    execute_command("LIN" + home_pos + "TOOL")
    commands = []
    for element in queue:
        if abs(element[0]) > 3000 or abs(element[1] > 3000):
            continue
        commands.extend(create_commands(element[0], element[1], element[2]))
    print(commands)

    while commands:
        execute_command(commands[0])
        commands.pop(0)

start()
sleep(20)

