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


import os
import sys
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Label, Button
from helpers.delta import SharedQueue
import threading

class TextUserInterface(App):

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("s", "start_sorting", "Start sorting process"),
    ]

    CSS_PATH = "textuserinterface.tcss"

    def __init__(self, app):
        super().__init__()
        self.depthaiApp = app
        self.value = ""

    def compose(self):
        yield Header()
        yield Footer()
        self.label_widget = Label("Test message")
        yield self.label_widget
        yield Button("sort", id="sort", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.exit(event.button.id)
        # todo

    def update_label(self):
        i = 0
        while not self.should_exit:
            i += 1
            self.value = self.depthaiApp.shared_queue.get_queue()
            self.label_widget.text = "Test message\n" + "\n".join(self.value) + '1'
            time.sleep(1)

    def on_load(self, event):
        threading.Thread(target=self.update_label, daemon=True).start()


    # def on_load(self, event):
    #     self.value = self.shared_queue.get_queue()
    #     self.add(Header("Shared Queue Example"))
    #     self.add(Footer(f"Value from SharedQueue: "))

# def main():
#     sq = SharedQueue()
#     sq.set_queue("custom data")


