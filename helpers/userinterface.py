from typing import Any, Coroutine
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from helpers.delta import SharedQueue


class DeltaTextUserInterfaceApp(App):

    BINDINGS = [("q", "quit()", "Quit TUI"),
               ("space", "test_key(4)", "Turn on sorting"),
               ("b", "toggle_dark", "Toggle dark mode"),
               ("w,up,k", "jog_movement(0, 1, 0)", "Move Up"),
               ("s,down,j", "jog_movement(0, -1, 0)", "Move Down"),
               ("a,left,h", "jog_movement(-1, 0, 0)", "Move Left"),
               ("d,right,l", "jog_movement(1, 0, 0)", "Move Right"),
               ("r,pageup", "jog_movement(0, 0, 1)", "Move Up"),
               ("f,pagedown", "jog_movement(0, 0, -1)", "Move Down")]

    def __init__(self, app):
        super().__init__()
        self.delta_client = app.delta_client
        self.shared_queue = app.shared_queue
        text_prompt_joined = "\n".join(app.text_prompt)
        self.text_prompt = str(text_prompt_joined)
        self.is_button_pressed = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Static(self.text_prompt)
        yield QueueDisplay("Init text user interface", self.shared_queue)

    # toggle dark mode after pressing "b"
    def action_toogle_dark(self) -> None:
        self.dark = not self.dark

    # turn OFF TUI after pressing "ESCAPE"
    def action_quit(self) -> Coroutine[Any, Any, None]:
        return super().action_quit()
    
    # turn ON sorting after pressing "SPACE"
    def action_turn_sort(self) -> None:
        self.delta_client.sort()

    # TODO make it async?
    # handle JOG movement, triggered by the arrow keys / j,k,l,i
    def action_jog_movement(self, x_str, y_str, z_str) -> None:
        self.delta_client.jog_operation(int(x_str), int(y_str), int(z_str))

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
