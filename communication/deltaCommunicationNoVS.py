import socket
from threading import Thread
from time import sleep
import argparse


###
use_godot = False
###

"""
     This program constantly updates queue for detected chocolate bars, and send move commands to robot delta 
"""

parser = argparse.ArgumentParser()
parser.add_argument("--device", help="Set 0 for running delta simulation or 1 for running on real delta",
                    type=int, choices=[0, 1], default=0)

# will be used later after
args = parser.parse_args()

if args.device == 1:
    use_godot = False
    print("Using real delta")
else:
    use_godot = True
    print("Using Godot simulation")


"""
    Boundaries for robot delta:
        z belongs to [-7000, -4000]
        for z == -4000 x and y belongs to [-3700, 3700]
        for z == -7000 x and y belongs to [-3000, 3000]
"""


HOST, PORT = "localhost", 2137
home_pos = "-1800-1800-4500"
obj_hover_height = "-4500"
obj_pickup_height = "-4900"
obj_drop_down_height = "-4800"
offset_threshold = 100  # how much can differ the real and set position
sleep_time = 0.2  # how long in seconds will the G_P command be send while checking if achieved position
queue = [(1900, 1300, 0), (1000, 0, 1), (50, 50, 3), (-50, -1500, 2)]  # later will be replaced with vision system return (x, y, type_of)

# put down location coordinates
put_location_1 = "+1000+1000"
put_location_2 = "+1000-1000"
put_location_3 = "-1000+1000"
put_location_4 = "-1000-1000"

"""
    Init communication with robot delta
"""

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
if args.device == 1:
    delta_host, delta_port = "localhost", 10  # todo change for delta ip
else:
    delta_host, delta_port = "localhost", 2137

try:
    sock.connect((delta_host, delta_port))
    print("Connected with robot delta")
except Exception as e:
    print("Not connected with robot delta")
    print(e)

def execute_command(command):
    global sock
    return_value = None
    prefix = command[0:3]

    if prefix == "G_P":
        sock.send("G_P".encode())
        recv = sock.recv(23).decode()
        return recv

    elif prefix == "LIN":
        print("Performing: ", command)
        set_x, set_y, set_z = get_coordinates(command)
        sock.send(command.encode())

        sock.recv(23)  # clear buffer
        sock.send("G_P".encode())
        sleep(0.3)
        recv = sock.recv(26).decode()
        curr_x, curr_y, curr_z = get_coordinates(recv)
        print("Current position: ", curr_x, " ", curr_y, " ", curr_z, " ")
        offsets = [abs(set_x - curr_x), abs(set_y - curr_y), abs(set_z - curr_z)]
        sleep(sleep_time)

    elif prefix == "TIM":
        timeout = command[3:6]
        sleep(int(timeout)//1000)

    # elif prefix == "REL":
    #     sock.send(command.encode())
    #     sock.recv(4)

    elif prefix == "TIM":
        timeout = command[3:6]
        sleep(int(timeout) // 1000)

    elif prefix == "JNT":
        pass

    elif prefix == "CIR":
        pass

    return


# todo update to enable controlling the suction cup and differentiate between picking up and putting down
def pick_up_command(coordinates):
    pick_up = ["LIN" + coordinates + obj_hover_height + "TOOL_",
               "LIN" + coordinates + obj_pickup_height + "TOOL_",
               "TIM" + str(100),
               "LIN" + coordinates + obj_hover_height + "TOOL_"]
    return pick_up


def dropping_down_command(drop_location):
    put_down = ["LIN" + drop_location + obj_hover_height + "TOOL_",
                "LIN" + drop_location + obj_drop_down_height + "TOOL_",
                "LIN" + drop_location + obj_hover_height + "TOOL_"]
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
            commands.extend(dropping_down_command(put_location_1))
        case 1:
            commands.extend(dropping_down_command(put_location_2))
        case 2:
            commands.extend(dropping_down_command(put_location_3))
        case 3:
            commands.extend(dropping_down_command(put_location_4))

    # return home command
    commands.append("LIN" + home_pos + "TOOL_")
    return commands


def start():

    # go home
    execute_command("LIN" + home_pos + "TOOL_")
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
