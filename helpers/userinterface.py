import threading
import os
import sys
import select


class UserInterface(threading.Thread):
    def __init__(self, shared_queue, text_prompt):
        super().__init__()
        self.shared_queue = shared_queue
        self.prompt = text_prompt
        self.running = True
        self.user_input = None

    def run(self):
        while self.running:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(self.prompt)
            print("Current Queue state is: ", end="")
            print(self.shared_queue.get_queue())
            print("Press newline (ENTER) to start sorting")
            self.user_input = UserInterface.non_blocking_input()
            if self.user_input:
                print(self.user_input)
                print("keypress detectied:")
                break

# todo fix non_blocking
    @staticmethod
    def non_blocking_input():
        # this method enables to check for certain keypress without blocking the program
        while sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
            line = sys.stdin.readline().strip()
            if line:
                return line

    def set_prompt(self, prompt):
        self.prompt = prompt

    def get_user_input(self):
        return self.user_input

    def stop(self):
        self.running = False
        # todo fix prompt
