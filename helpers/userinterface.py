from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from delta import SharedQueue
import threading
import time

class QueueDisplay(Static):
    def on_mount(self) -> None:
        self.set_interval(1, self.update_queue)

    def update_queue(self) -> None:
        self.update(str(sq.get_queue()))



class DeltaTextUserInterfaceApp(App):

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

    def __init__(self, sq):
        super().__init__()
        self.sq = sq

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield QueueDisplay("Test messege")

    # toggle dark mode after pressing "d"
    def action_toogle_dark(self) -> None:
        self.dark = not self.dark

    def on_mount(self) -> None:
        self.title = "Robot Delta Text User Interface"

class SharedQueueTest(SharedQueue):
        def update_queue_periodically(self):
            while True:
                # Simulate updating the queue with new data (replace this with your actual data update logic)
                new_data = time.time()
                self.set_queue(new_data)
                
                # Sleep for a while before the next update
                time.sleep(1)  # Update every 1 second (adjust as needed)


# later will be put into app.py
if __name__ == "__main__":
    sq = SharedQueueTest()
    th1 = threading.Thread(target=sq.update_queue_periodically)
    th1.start()
    time.sleep(2)
    app = DeltaTextUserInterfaceApp(sq)
    app.run()









# import curses
# import threading
# import time


# class TextUserInterface(threading.Thread):
#     def __init__(self, app):
#         super().__init__()
#         self.app = app
#         self.running = True
#
#     def run(self):
#         # Initialize curses
#         stdscr = curses.initscr()
#         curses.noecho()
#         curses.cbreak()
#         stdscr.keypad(True)
#
#         try:
#             while self.running:
#                 stdscr.clear()
#                 stdscr.addstr(0, 0, "Press 'q' to quit the TUI.")
#
#                 # Display robot information
#                 text_prompt = self.app.text_prompt
#                 robot_info = self.app.shared_queue.get_queue()
#
#                 combined_string = text_prompt + "\n".join(robot_info)
#                 stdscr.addstr(2, 0, "Test message")
#
#                 stdscr.refresh()
#                 time.sleep(1)  # Update every second
#
#         finally:
#             # Cleanup curses
#             curses.nocbreak()
#             stdscr.keypad(False)
#             curses.echo()
#             curses.endwin()
#
#     def stop(self):
#         self.running = False


# import os
# import sys
# from textual.app import App, ComposeResult
# from textual.widgets import Header, Footer, Label, Button, Placeholder
# from helpers.delta import SharedQueue
# import threading

# class TextUserInterface(App):

#     BINDINGS = [
#         ("d", "toggle_dark", "Toggle dark mode"),
#         ("s", "start_sorting", "Start sorting process"),
#         ("q", "quit", "Quit App")
#     ]

#     CSS_PATH = "textuserinterface.tcss"

#     def __init__(self, app):
#         super().__init__()
#         self.depthaiApp = app
#         self.value = ""
#         self.label_widget = Label("Test message")

#     def compose(self):
#         yield Header(Placeholder)
#         yield Footer()
#         yield self.label_widget

#     def update_label(self):
#         i = 0
#         while not self.should_exit:
#             i += 1
#             self.value = self.depthaiApp.shared_queue.get_queue()
#             self.label_widget.update(str(i))
#             time.sleep(1)

#     def on_load(self, event):
#         threading.Thread(target=self.update_label, daemon=True).start()


    # def on_load(self, event):
    #     self.value = self.shared_queue.get_queue()
    #     self.add(Header("Shared Queue Example"))
    #     self.add(Footer(f"Value from SharedQueue: "))

# def main():
#     sq = SharedQueue()
#     sq.set_queue("custom data")


