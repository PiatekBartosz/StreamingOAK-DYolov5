import argparse
import sys
import socket

# get user local IP to host over LAN the video, note the json file will be hosted over localhost
hostname = socket.gethostname()
IPAddress = socket.gethostbyname(hostname)

# parsing
parser = argparse.ArgumentParser()
parser.add_argument("--device", help="Choose delta simulation or real delta (default: simulation)",
                    type=int, choices=[0, 1], default=0)
parser.add_argument("--ip", help="Set http server ip-s", type=str, default=IPAddress)
parser.add_argument("--vision_only", help="Set 1 for only vision system functionality",
                    type=int, choices=[0, 1], default=0)

args = parser.parse_args()
print(args)