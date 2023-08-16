import threading

class UserInterface(threading.Thread):
    def __init__(self, shared_queue):
        super().__init__()
        self.shared_queue = shared_queue
        self.prompt = None

    def run(self):
        while self.running:
            self.user_input = input(prompt)

    def set_prompt(self, prompt):
        self.prompt = prompt

    def get_user_input(self):
        return self.user_input

    def stop(self):
        self.running = False
        # todo fix prompt
