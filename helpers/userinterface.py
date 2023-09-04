from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive
from helpers.delta import SharedQueue
import threading
import time


class DeltaTextUserInterfaceApp(App):

    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"),
                ("s", "toggle_sort", "Turn on sorting"),
                ("q", "quit", "Quit TUI")]

    def __init__(self, shared_queue: SharedQueue):
        super().__init__()
        self.shared_queue = shared_queue

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield QueueDisplay("Init text user interface", self.shared_queue)

    # toggle dark mode after pressing "d"
    def action_toogle_dark(self) -> None:
        self.dark = not self.dark

    def on_mount(self) -> None:
        self.title = "Robot Delta Text User Interface"


class QueueDisplay(Static):
    def __init__(self, text_prompt, shared_queue):
        super().__init__(text_prompt)
        self.shared_queue = shared_queue

    def on_mount(self) -> None:
        # the queue will be updated with a given interval
        interval = 0.5
        self.set_interval(interval, self.update_queue)

    def update_queue(self) -> None:
        self.update(str(self.shared_queue.get_queue()))

# from textual.app import App, ComposeResult
# from textual.widgets import Header, Footer, Static
# from textual.reactive import reactive
# from delta import SharedQueue
# import threading
# import time

# class QueueDisplay(Static):
#     def __init__(self, sq):
#         super().__init__()
#         self.sq = sq


#     def on_mount(self) -> None:
#         self.set_interval(1, self.update_queue)

#     def update_queue(self) -> None:
#         self.update(str(self.sq.get_queue()))



# class DeltaTextUserInterfaceApp(App):

#     BINDINGS = [("d", "toggle_dark", "Toggle dark mode")]

#     def __init__(self, sq):
#         super().__init__()
#         self.sq = sq

#     def compose(self) -> ComposeResult:
#         yield Header()
#         yield Footer()
#         yield QueueDisplay(self.sq)

#     # toggle dark mode after pressing "d"
#     def action_toogle_dark(self) -> None:
#         self.dark = not self.dark

#     def on_mount(self) -> None:
#         self.title = "Robot Delta Text User Interface"

# class SharedQueueTest(SharedQueue):
#         def update_queue_periodically(self):
#             while True:
#                 # Simulate updating the queue with new data (replace this with your actual data update logic)
#                 new_data = time.time()
#                 self.set_queue(new_data)
                
#                 # Sleep for a while before the next update
#                 time.sleep(1)  # Update every 1 second (adjust as needed)


# # later will be put into app.py
# if __name__ == "__main__":
#     sq = SharedQueueTest()
#     th1 = threading.Thread(target=sq.update_queue_periodically)
#     th1.start()
#     time.sleep(2)
#     app = DeltaTextUserInterfaceApp(sq)
#     app.run()