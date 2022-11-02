import socket
import threading
from time import sleep
import json
import sys

"""
     This program constantly updates queue for detected chocolate bars, and send move commands to robot delta 
"""

"""
    Boundaries for robot delta:
        z belongs to [-7000, -4000]
        for z == -4000 x and y belongs to [-3700, 3700]
        for z == -7000 x and y belongs to [-3000, 3000]
"""

# store predictions acquired by the vision system
queue = []
queue_lock = threading.Lock()

"""
(x_pos, y_pos, type_of_chocolate_bar)
type_of_chocolate_bar:
    0 -> 3-bit
    1 -> Mars
    2 -> Milkyway
    3 -> Snickers
"""

# todo parse the arguments to see if we want to use simulation or real delta set global speed for all commands


"""
    Init Vision system
"""

vision_stop = False
vision_host, vision_port = "localhost", 8070
vision_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    vision_sock.connect((vision_host, vision_port))
    print("Connected to vision system server")
except Exception as e:
    print(e)


# vision system handle
def get_data():
    global queue
    global queue_lock
    global vision_sock
    vision_sock.recv(1024).decode()  # clear buffer
    recv_str = vision_sock.recv(2048).decode()

    # parse the input
    splitted_str = recv_str.split("\n")
    for s in splitted_str:
        s_replaced = s.replace("\r", "")

        # compute only first valid input
        if is_valid_json(s_replaced):
            queue_lock.acquire()
            queue = parse_data_from_string(s_replaced)
            print("Updated queue with: ", queue)
            queue_lock.release()
            break


# vision system helper functions
def parse_data_from_string(s_replaced):
    dic = json.loads(s_replaced)
    local_queue = []
    for index, (name, detections) in enumerate(dic.items()):
        if detections:
            for detection in detections:
                x, y = detection['middle_transformed']
                # normalize x, y
                if 0 <= x <= 416 and 0 <= x <= 416:
                    x = x / 416
                    y = y / 416
                    local_queue.append((x, y, index))

    return local_queue


def is_valid_json(s):
    if len(s) < 65:
        return False
    if s[0] != "{" or s[-1] != "}":
        return False
    return True


"""
    Init communication with robot delta
"""

# variables used to
delta_host, delta_port = "localhost", 2137
home_pos = "-2000-2000-4500"
obj_hover_height = "-4500"
obj_pickup_height = "-7000"
offset_threshold = 100  # how much can differ the real and set position
sleep_time = 1  # how long in seconds will the G_P command be send while checking if achieved position
calibration_box_size = (6000, 6000)  # size of the square that is used when calibrating delta vision system

# put down location coordinates
put_location_1 = "+1000+1000"
put_location_2 = "+1000+1000"
put_location_3 = "+1000+1000"
put_location_4 = "+1000+1000"

delta_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    delta_sock.connect((delta_host, delta_port))
    print("Connected with robot delta")
except Exception as e:
    print(e)


def execute_command(command):
    global delta_sock
    return_value = None
    prefix = command[0:3]

    if prefix == "G_P":
        delta_sock.send("G_P".encode())
        recv = delta_sock.recv(23).decode()
        return recv

    elif prefix == "LIN":
        print("Performing: ", command)
        set_x, set_y, set_z = get_coordinates(command)
        delta_sock.send(command.encode())
        sleep(sleep_time)
        while True:
            delta_sock.recv(23)  # clear buffer
            delta_sock.send("G_P".encode())
            sleep(0.3)
            recv = delta_sock.recv(26).decode()
            curr_x, curr_y, curr_z = get_coordinates(recv)
            print("Current position: ", curr_x, " ", curr_y, " ", curr_z, " ")

            offsets = [abs(set_x - curr_x), abs(set_y - curr_y), abs(set_z - curr_z)]

            # todo consider checking for moving
            if max(offsets) <= offset_threshold:
                break
            sleep(sleep_time)

    elif prefix == "TIM":
        timeout = command[3:6]
        sleep(int(timeout) // 1000)

    elif prefix == "JNT":
        pass

    elif prefix == "CIR":
        pass

    sleep(sleep_time)
    return


# todo update to enable controlling the suction cup and differentiate between picking up and putting down
def pick_up_command(coordinates):
    pick_up = ["LIN" + coordinates + obj_hover_height + "TOOL_",
               "LIN" + coordinates + obj_pickup_height + "TOOL_", "TIM" + str(2000),
               "LIN" + coordinates + obj_hover_height + "TOOL_"]
    return pick_up


def putting_down_command(put_location):
    put_down = ["LIN" + put_location + obj_hover_height + "TOOL_",
                "LIN" + put_location + obj_pickup_height + "TOOL_", "TIM" + str(2000),
                "LIN" + put_location + obj_hover_height + "TOOL_"]
    return put_down


def create_commands(x, y, type_of):
    commands = []

    if x >= 0:
        x = str(x)
        missing = 4 - len(x)  # we want to achieve 4 digit format
        x = "+" + "0" * missing + x
    else:
        x = str(x)[1:]
        missing = 4 - len(x)
        x = "-" + "0" * missing + x

    if y >= 0:
        y = str(y)
        missing = 4 - len(y)  # we want to achieve 4 digit format
        y = "+" + "0" * missing + y
    else:
        y = str(y)[1:]
        missing = 4 - len(y)
        y = "-" + "0" * missing + y

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
    commands.append("LIN" + home_pos + "TOOL_")
    return commands


def sort(local_queue):
    # create commands to move every detected object
    commands = []
    for element in local_queue:
        # get x, y, normalize it regarding calib box size
        x = int(element[0] * calibration_box_size[0] - calibration_box_size[0])
        y = int(element[1] * calibration_box_size[1] - calibration_box_size[1])

        if abs(x) > 3000 or abs(y) > 3000:
            continue
        commands.extend(create_commands(x, y, element[2]))
    print(commands)

    while commands:
        execute_command(commands[0])
        commands.pop(0)


def get_coordinates(s):
    x = int(s[4:8]) if s[3] == "+" else int(s[3:8])
    y = int(s[9:13]) if s[8] == "+" else int(s[8:13])
    z = int(s[14:18]) if s[13] == "+" else int(s[13:18])
    return x, y, z


"""
    Program thread and loops
"""


def vision_system_loop():
    while True:
        get_data()

# todo fix infite loop, set break conditions

def delta_loop():
    global queue
    while True:
        queue_lock.acquire()
        if queue:
            sort(queue)
            queue = []
            break

        queue_lock.release()
        sleep(3)


th1 = threading.Thread(target=vision_system_loop)
th1.start()

th2 = threading.Thread(target=delta_loop)
th2.start()

th1.join()
th2.join()

vision_sock.close()
delta_sock.close()

