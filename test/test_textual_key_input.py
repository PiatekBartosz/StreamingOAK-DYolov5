from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
import threading


class TestApp(App):
     BINDINGS = [("escape", "quit()", "Quit TUI"),
               ("b", "toggle_dark", "Toggle dark mode"),
               ("space", "test_key(4)", "Turn on sorting"),
               ("w,up,k", "test_key(0)", "Move Up"),
               ("s,down,j", "test_key(1)", "Move Down"),
               ("a,left,h", "test_key(2)", "Move Left"),
               ("d,right,l", "test_key(3)", "Move Right")]

     def __init__(self):
          super().__init__()
          self.shared_text = SharedText()

     def on_mount(self):
          self.title = "Test key callbacks"

     def compose(self) -> ComposeResult:
          yield Header()
          yield Footer()
          yield TextBoxWidget(self.shared_text)

     def action_test_key(self, num):
          self.shared_text.set_text(str(num))

     def action_quit(self):
          super().action_quit()


class TextBoxWidget(Static):
     def __init__(self, shared_text):
          super().__init__()
          self.shared_text = shared_text

     def on_mount(self):
          self.set_interval(0.5, self.update_queue)

     def update_queue(self):
          self.update(self.shared_text.get_text())

             
class SharedText:
     def __init__(self):
          self.text = "Press key to test callbacks"
          self.lock = threading.Lock()

     def set_text(self, text):
          with self.lock:
               self.text = text

     def get_text(self) -> str:
          with self.lock:
               return str(self.text)


app = TestApp()
app.run()
