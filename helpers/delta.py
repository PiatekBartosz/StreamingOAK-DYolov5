import socket
import threading
from time import sleep


class RobotDeltaClient(threading.Thread):
    def __init__(self, delta_host, delta_port, shared_queue):
        super().__init__()  # used to call threading.Thread constructor
        self.HOST, self.PORT = delta_host, delta_port
        self.obj_hover_height = "+4000"
        self.obj_pickup_height = "+0000"
        self.error = 100  # how much can differ the real and set position
        self.queue_hardcoded = [(2500, 5300, 0), (2444, 2555, 1)]
        self.shared_queue = shared_queue

        # put down location coordinates
        self.put_location_1 = "+1000+1000"
        self.put_location_2 = "+1000-1000"
        self.put_location_3 = "-1000+1000"
        self.put_location_4 = "-1000-1000"

        self.sock = None
        self.running = True

    def run(self):
        connected = False
        # constantly try to be connected
        while not connected:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.HOST, self.PORT))
                connected = True

                # set start position
                self.sock.sendall(bytes("LIN+4500+0000+0100TOOL", "utf-8"))

                # wait for user to start sorting
                while self.running:
                    if self.shared_queue.get_sorting():
                        if self.shared_queue.get_queue() is not None:
                            x, y, type_of = self.queue[0][0], self.queue[0][1], self.queue[0][2]
                            commands = self.create_commands(x, y, type_of)

                            while commands:
                                x_set, y_set, z_set = self.get_coordinates(commands[0])
                                self.sock.send(bytes(commands[0], "utf-8"))
                                self.wait_until_achieved_pos(x_set, y_set, z_set)
                                commands.pop(0)
                            self.queue.pop(-1)
                            print("end")
                        self.shared_queue.stop_sorting()
                    else:
                        sleep(0.1)
            except socket.error:
                # sleep for 2s if lost connection
                sleep(2)



    def get_pos(self):
        global current_position
        while thread1.is_alive():
            self.sock.send(bytes("G_P", "utf-8"))
            recv = self.et_coordinates(self.sock.recv(128), "utf-8")
            current_position = recv
            sleep(0.03)

    # parse x, y, z position from robot callbackz
    @staticmethod
    def get_coordinates(s):
        x = int(s[4:8]) if s[3] == "+" else int(s[3:8]) * (-1)
        y = int(s[9:13]) if s[8] == "+" else int(s[8:13]) * (-1)
        z = int(s[14:18]) if s[13] == "+" else int(s[13:18]) * (-1)
        # todo convert to number normalize x, y, z
        return x, y, z

    def create_commands(self, x, y, type_of):
        commands = []

        x = "+" + str(x) if x >= 0 else str(x)
        y = "+" + str(y) if y >= 0 else str(y)

        # pick up object
        commands.extend(self.pick_up_command(x + y))

        # put down to specific location and go to default position
        match type_of:
            case 0:
                commands.extend(self.putting_down_command(self.put_location_1))
            case 1:
                commands.extend(self.putting_down_command(self.put_location_2))
            case 2:
                commands.extend(self.putting_down_command(self.put_location_3))
            case 3:
                commands.extend(self.putting_down_command(self.put_location_4))

        # return home command
        commands.append("LIN+4500+0000+0000TOOL")
        return commands

    # todo update to enable controlling the suction cup and differentiate between picking up and putting down
    def pick_up_command(self, coordinates):
        pick_up = ["LIN" + coordinates + self.obj_hover_height + "TOOL",
                   "LIN" + coordinates + self.obj_pickup_height + "TOOL",
                   "LIN" + coordinates + self.obj_hover_height + "TOOL"]
        return pick_up

    def putting_down_command(self, put_location):
        put_down = ["LIN" + put_location + self.obj_hover_height + "TOOL",
                    "LIN" + put_location + self.obj_pickup_height + "TOOL",
                    "LIN" + put_location + self.obj_hover_height + "TOOL"]
        return put_down
    def wait_until_achieved_pos(self, x_set, y_set, z_set):
        error = 100
        x_curr, y_curr, z_curr = current_position
        while abs(x_curr - x_set) > error or abs(y_curr - y_set) > error or abs(z_curr - z_set) > error:
            x_curr, y_curr, z_curr = current_position
            sleep(0.01)
        return


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
            return self.data

    def start_sorting(self):
        self.want_to_sort = True

    def stop_sorting(self):
        self.want_to_sort = False

    def get_sorting(self):
        return self.want_to_sort

    # def start_sorting(self):


