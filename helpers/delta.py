import socket
import threading
from time import sleep


class RobotDeltaClient(threading.Thread):
    def __init__(self, delta_host, delta_port, shared_queue, hardcoded_queue_bool):
        super().__init__()  # used to call threading.Thread constructor
        self.HOST, self.PORT = delta_host, delta_port
        self.home_pos = "+0000-1900-4500"
        self.obj_hover_height = "-4100"
        self.obj_pickup_height = "-5550"
        self.obj_drop_down_height = "-5000"
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
        self.robot_busy = False  # used to prevent automatic sorting and JOG simultaneously 

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
        # prevent set robot busy varaible to prevent JOG operation
        self.robot_busy = True

        # get local queue -> depends if hardcoded queue option has been chosen
        if not self.hardcoded_queue_bool:
            local_queue = self.shared_queue.get_queue()
        else:
            local_queue = self.queue_hardcoded

        commands = []

        # TODO fix

        for detection in local_queue:
            # normalize element size
            x, y, type_of_detection = detection[0], detection[1], detection[2]

            if 0 <= x <= 416 and 0 <= y <= 416:

                # calculate the coordinates with correct axis orientation (x_orient, y_orient)
                x_norm_orient = int(x * self.calibration_box_size[0] - self.calibration_box_size[0]/2.0) * self.x_orient
                y_norm_orient = int(y * self.calibration_box_size[1] - self.calibration_box_size[1]/2.0) * self.y_orient

                # check if it's in the sorting range
                if abs(x_norm_orient) > self.calibration_box_size[0]//2 or abs(y_norm_orient) > self.calibration_box_size[1]//2:
                    continue

                commands.extend(self.create_commands(x_norm_orient, y_norm_orient, type_of_detection))

            else: 
                continue

        while commands:
            self.execute_command(commands[0])
            commands.pop(0)

        # enable JOG oepration
        self.robot_busy = False

    def jog_operation(self, x, y, z):
        if not self.robot_busy:
            prescaler = 1000
            x_formated = self.get_4_digit_format(x * prescaler)
            y_formated = self.get_4_digit_format(y * prescaler)
            z_formated = self.get_4_digit_format(z * prescaler)

            command = "JOG" + x_formated + y_formated + z_formated + "TOOL_"
            self.execute_command(command)


    def execute_command(self, command):
        prefix = command[0:3]

        if prefix == "G_P":
            self.delta_sock.send("G_P".encode())
            recv = self.delta_sock.recv(23).decode()
            return recv

        elif prefix == "LIN":
            # add velocity
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

        # example JOG command: JOG+0000+0000-5000TOOL_
        elif prefix == "JOG":
            self.delta_sock.send(command.encode())  # send JOG command
            sleep(0.3)
            self.delta_sock.recv(23)  # clear JOG return value

        elif prefix == "TIM":
            timeout = command[3:6]
            sleep(int(timeout) // 1000)

        elif prefix == "JNT":
            pass

        elif prefix == "CIR":
            pass

        return

    def pick_up_command(self, coordinates):
        pick_up = ["LIN" + coordinates + self.obj_hover_height + "TOOL_" + "V0100",
                "LIN" + coordinates + self.obj_pickup_height + "TOOL_" + "V0100",
                "RELB",
                "LIN" + coordinates + self.obj_hover_height + "TOOL_" + "V0100"]
        return pick_up


    def dropping_down_command(self, drop_location):
        put_down = ["LIN" + drop_location + self.obj_hover_height + "TOOL_" + "V0100",
                    "LIN" + drop_location + self.obj_drop_down_height + "TOOL_" + "V0100",
                    "RELA",
                    "LIN" + drop_location + self.obj_hover_height + "TOOL_" + "V0100"]
        return put_down


    def create_commands(self, x, y, type_of):
        commands = []

        # the is not aligned with y-axis
        x_offset = 0
        y_offset = 200

        x = (-1)*x + x_offset
        y = (-1)*y + y_offset

        x = get_4_digit_format(x)
        y = get_4_digit_format(y)

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
        commands.append("LIN" + self.home_pos + "TOOL_" + "V0100")
        return commands


    def get_coordinates(self, s):
        x = int(s[4:8]) if s[3] == "+" else int(s[3:8])
        y = int(s[9:13]) if s[8] == "+" else int(s[8:13])
        z = int(s[14:18]) if s[13] == "+" else int(s[13:18])
        return x, y, z
    

    def get_4_digit_format(self, num) -> str:
        if num >= 0:
            num = str(num)
            missing = 4 - len(num)  # we want to achieve 4 digit format
            result = "+" + "0" * missing + num
        else:
            num = str(num)[1:]
            missing = 4 - len(num)
            result = "-" + "0" * missing + num
        return result



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
                return self.data
            else:
                return "No detections"
