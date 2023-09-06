import socket
import threading
from time import sleep


class RobotDeltaClient(threading.Thread):
    def __init__(self, delta_host, delta_port, shared_queue, hardcoded_queue_bool):
        super().__init__()  # used to call threading.Thread constructor
        self.HOST, self.PORT = delta_host, delta_port
        self.home_pos = "+0000-1900-4500"
        self.obj_hover_height = "+4000"
        self.obj_pickup_height = "+0000"
        self.obj_drop_down_height = "-5500"
        self.error = 100  # how much can differ the real and set position
        self.queue_hardcoded = [(200, 200, 0), (100, 100, 1)]
        self.shared_queue = shared_queue
        self.hardcoded_queue_bool = hardcoded_queue_bool
        self.exceptions = []
        self.offset_threshold = 500  # how much can differ the real and set position
        self.sleep_time = 1  # how long in seconds will the G_P command be send while checking if achieved position
        self.calibration_box_size = (3800, 3800)  # size of the square that is used when calibrating delta vision system
        self.x_orient, self.y_orient = -1, 1  # x_camera, x_delta relation as well as y_camera, y_delta
        self.delta_sock_connected = False

        # put down location coordinates
        self.put_location_1 = "+1000+1000"
        self.put_location_2 = "+1000-1000"
        self.put_location_3 = "-1000+1000"
        self.put_location_4 = "-1000-1000"

        self.sock = None

        # connect to delta robot TODO prompt that connected to delta
        try:
            self.delta_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.delta_sock.connect((self.HOST, self.PORT))
            self.delta_sock_connected = True

        except Exception as e:
            print("Not connected with vision system")
            print(e)
            self.exceptions.append(e)
 
    def sort(self):
        # get local queue -> depends if hardcoded queue option has been chosen
        if not self.hardcoded_queue_bool:
            local_queue = self.shared_queue.get_queue()
        else:
            local_queue = self.queue_hardcoded

        if not isinstance(local_queue, list):
            return

        commands = []

        for detection in local_queue:
            # normalize element size
            x, y, type_of_detection = detection[0], detection[1], detection[2]

            if 0 <= x <= 416 and 0 <= y <= 416:
                x_norm, y_norm = x / 416, y / 416

                # calculate the coordinates with correct axis orientation (x_orient, y_orient)
                x_norm_orient = int(x_norm * self.calibration_box_size[0] - self.calibration_box_size[0]/2.0) * self.x_orient
                y_norm_orient = int(y_norm * self.calibration_box_size[1] - self.calibration_box_size[1]/2.0) * self.y_orient

                # check if it's in the sorting range
                if abs(x_norm_orient) > self.calibration_box_size[0]//2 or abs(y_norm_orient) > self.calibration_box_size[1]//2:
                    continue

                commands.extend(self.create_commands(x_norm_orient, y_norm_orient, type_of_detection))

            else: 
                continue

        while commands:
            self.execute_command(commands[0])
            commands.pop(0)

    def execute_command(self, command):
        prefix = command[0:3]

        if prefix == "G_P":
            self.delta_sock.send("G_P".encode())
            recv = self.delta_sock.recv(23).decode()
            return recv

        elif prefix == "LIN":
            # add velocity
            print("Performing: ", command)
            self.delta_sock.send(command.encode())  # send LIN command
            sleep(0.3)
            self.delta_sock.recv(28)  # clear LIN return value
            if self.PORT != 2137:
                while True:
                    self.delta_sock.send("G_P".encode())
                    sleep(0.3)
                    recv = self.delta_sock.recv(23).decode()
                    if recv[-3] == "N":
                        break
            else:
                sleep(1)

        elif prefix == "REL":
            sleep(0.3)
            self.delta_sock.send(command.encode())
            sleep(0.3)
            self.delta_sock.recv(4)
            sleep(0.3)

        elif prefix == "TIM":
            timeout = command[3:6]
            sleep(int(timeout) // 1000)

        elif prefix == "JNT":
            pass

        elif prefix == "CIR":
            pass

        return

    def pick_up_command(self, coordinates):
        pick_up = ["LIN" + coordinates + self.obj_hover_height + "TOOL_" + "V0030",
                "LIN" + coordinates + self.obj_pickup_height + "TOOL_" + "V0030",
                "RELB",
                "LIN" + coordinates + self.obj_hover_height + "TOOL_" + "V0010"]
        return pick_up


    def dropping_down_command(self, drop_location):
        put_down = ["LIN" + drop_location + self.obj_hover_height + "TOOL_" + "V0010",
                    "LIN" + drop_location + self.obj_drop_down_height + "TOOL_" + "V0010",
                    "RELA",
                    "LIN" + drop_location + self.obj_hover_height + "TOOL_" + "V0030"]
        return put_down


    def create_commands(self, x, y, type_of):
        commands = []

        # the is not aligned with y-axis
        x_offset = 0
        y_offset = 200

        x = (-1)*x + x_offset
        y = (-1)*y + y_offset

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
        commands.extend(self.pick_up_command(x + y))

        # put down to specific location and go to default position
        # the type_of represents the type of the project
        if type_of == 0:
            commands.extend(self.dropping_down_command(self.put_location_1))
        elif type_of == 1:
            commands.extend(self.dropping_down_command(self.put_location_2))
        elif type_of == 2:
            commands.extend(self.dropping_down_command(self.put_location_3))
        elif type_of == 3:
            commands.extend(self.dropping_down_command(self.put_location_3))
        elif type_of == 4:
            commands.extend(self.dropping_down_command(self.put_location_3))
        elif type_of == 5:
            commands.extend(self.dropping_down_command(self.put_location_2))
        elif type_of == 6:
            commands.extend(self.dropping_down_command(self.put_location_2))
        elif type_of == 7:
            commands.extend(self.dropping_down_command(self.put_location_1))
        elif type_of == 8:
            commands.extend(self.dropping_down_command(self.put_location_2))
        else:
            commands.extend(self.dropping_down_command(self.put_location_2))

        # return home command
        commands.append("LIN" + self.home_pos + "TOOL_" + "V0030")
        return commands


    def get_coordinates(s):
        x = int(s[4:8]) if s[3] == "+" else int(s[3:8])
        y = int(s[9:13]) if s[8] == "+" else int(s[8:13])
        z = int(s[14:18]) if s[13] == "+" else int(s[13:18])
        return x, y, z



class SharedQueue:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()
        self.want_to_sort = False

    def set_queue(self, value):
        with self.lock:
            self.data = value

    def get_queue(self):
        with self.lock:
            if self.data:
                return str(self.data)
            else:
                return "No detections"
