import socket
import threading
from time import sleep
import json
import argparse
from pynput.keyboard import Key, Listener
import re

parser_com = argparse.ArgumentParser()
parser_com.add_argument("--device", help="Set 0 for running delta simulation or 1 for running on real delta",
                        type=int, choices=[0, 1], default=0)
parser_com.add_argument("--ip", help="Set ip of vision system host (defult: 127.0.0.1)",
                        type=str, default="127.0.0.1")

args = parser_com.parse_args()

queue = []
queue_lock = threading.Lock()

"""
    Values stored in queue:
    (x_pos, y_pos, type_of_chocolate_bar)
    type_of_chocolate_bar:
        0 -> 3-bit
        1 -> Mars
        2 -> Milkyway
        3 -> Snickers
"""

"""
    Init Vision system
"""

try:
    vision_host, vision_port = args.ip, 8070
    vision_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    vision_sock.connect((vision_host, vision_port))
    print(f"Connected to vision system server ({vision_host},{vision_port})")

except Exception as e:
    print("Not connected with vision system")
    print(e)


"""
    Init communication with robot delta
"""

try:
    if args.device == 0:
        delta_host, delta_port = "localhost", 2137
    else:
        delta_host, delta_port = "192.168.0.155", 10
    delta_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    delta_sock.connect((delta_host, delta_port))
    print(f"Connected to robot delta: ({delta_host},{delta_port})")

except Exception as e:
    print("Not connected to robot delta")
    print(e)


"""
    Vision system loop
"""


def vision_system_loop(queue_lock):
    global queue
    first = True
    while True:
        recv = vision_sock.recv(1024).decode()
        splited_strings = recv.split("\n")
        for s in splited_strings:
            s = s.replace("\r", "")
            if is_valid_json(s):
                if not queue_lock.locked():
                    new_queue = parse_data_from_string(s)
                    with queue_lock:
                        queue = new_queue
                    break
                else:
                    continue


def is_valid_json(s):
    pattern = r'^\{("[\w-]*":\s*.*,?){9}\}$'
    return re.match(pattern, s)


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


"""
Sorting loop
"""
home_pos = "+0000-1900-4500"

obj_hover_height = "-4500"
obj_pickup_height = "-6280"
obj_drop_down_height = "-5500"
offset_threshold = 500  # how much can differ the real and set position
sleep_time = 1  # how long in seconds will the G_P command be send while checking if achieved position
calibration_box_size = (3800, 3800)  # size of the square that is used when calibrating delta vision system
x_orient, y_orient = -1, 1  # x_camera, x_delta relation as well as y_camera, y_delta

# put down location coordinates
put_location_1 = "-2000-2000"
put_location_2 = "+2000-2000"
put_location_3 = "+1900+1900"
put_location_4 = "+1900+1900"


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
        sleep(1)
        # while True:
        #     delta_sock.recv(23)  # clear buffer
        #     delta_sock.send("G_P".encode())
        #     sleep(0.3)
        #     recv = delta_sock.recv(26).decode()
        #     curr_x, curr_y, curr_z = get_coordinates(recv)
        #     print("Current position: ", curr_x, " ", curr_y, " ", curr_z, " ")
        #
        #     offsets = [abs(set_x - curr_x), abs(set_y - curr_y), abs(set_z - curr_z)]
        #
        #     if max(offsets) <= offset_threshold:
        #         break
        #     sleep(sleep_time)

    elif prefix == "REL":
        delta_sock.send(command.encode())
        delta_sock.recv(4)

    elif prefix == "TIM":
        timeout = command[3:6]
        sleep(int(timeout) // 1000)

    elif prefix == "JNT":
        pass

    elif prefix == "CIR":
        pass

    sleep(0.3)
    return


def pick_up_command(coordinates):
    pick_up = ["LIN" + coordinates + obj_hover_height + "TOOL_",
               "LIN" + coordinates + obj_pickup_height + "TOOL_",
               "RELB",
               "LIN" + coordinates + obj_hover_height + "TOOL_"]
    return pick_up


def dropping_down_command(drop_location):
    put_down = ["LIN" + drop_location + obj_hover_height + "TOOL_",
                "LIN" + drop_location + obj_drop_down_height + "TOOL_",
                "RELA",
                "LIN" + drop_location + obj_hover_height + "TOOL_"]
    return put_down


def create_commands(x, y, type_of):
    commands = []

    x = (-1)*x
    y = (-1)*y

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
            commands.extend(dropping_down_command(put_location_1))
        case 1:
            commands.extend(dropping_down_command(put_location_1))
        case 2:
            commands.extend(dropping_down_command(put_location_1))
        case 3:
            commands.extend(dropping_down_command(put_location_1))
        case 4:
            commands.extend(dropping_down_command(put_location_1))
        case 5:
            commands.extend(dropping_down_command(put_location_1))
        case 6:
            commands.extend(dropping_down_command(put_location_2))
        case 7:
            commands.extend(dropping_down_command(put_location_1))
        case 8:
            commands.extend(dropping_down_command(put_location_2))

    # return home command
    commands.append("LIN" + home_pos + "TOOL_")
    return commands


def get_coordinates(s):
    x = int(s[4:8]) if s[3] == "+" else int(s[3:8])
    y = int(s[9:13]) if s[8] == "+" else int(s[8:13])
    z = int(s[14:18]) if s[13] == "+" else int(s[13:18])
    return x, y, z


def sort(local_queue):
    # create commands to move every detected object
    commands = []
    for element in local_queue:
        # get x, y, normalize it according to calib box size
        x = int(element[0] * calibration_box_size[0] - calibration_box_size[0]/2) * x_orient
        y = int(element[1] * calibration_box_size[1] - calibration_box_size[1]/2) * y_orient

        if abs(x) > 1900 or abs(y) > 1900:
            continue
        commands.extend(create_commands(x, y, element[2]))
    print(commands)

    while commands:
        execute_command(commands[0])
        commands.pop(0)


def on_press(key, ql):
    print(queue)
    if key == Key.space:
        with ql:
            print("Starting sort, current queue: ", queue)
            sort(queue)


def sort_loop(queue_lock):
    # lambda function in used to pass queue_lock as an argument
    with Listener(on_press=lambda event: on_press(event, ql=queue_lock)) as listener:
        listener.join()


th1 = threading.Thread(target=vision_system_loop, args=(queue_lock,))
th1.start()

th2 = threading.Thread(target=sort_loop, args=(queue_lock,))
th2.start()

th1.join()
th2.join()
