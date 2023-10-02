from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
import threading
import socket


class TestApp(App):
     BINDINGS = [("q", "quit()", "Quit TUI"),
               ("b", "toggle_dark", "Toggle dark mode"),
            #    ("space", "test_key(4)", "Turn on sorting"),
               ("w,up,k", "test_key(0)", "Move Up"),
               ("s,down,j", "test_key(1)", "Move Down"),
               ("a,left,h", "test_key(2)", "Move Left"),
               ("d,right,l", "test_key(3)", "Move Right"),
               ("r,pageup", "test_key(5)", "Move Up"),
               ("f,pagedown", "test_key(6)", "Move Down")]

     def __init__(self):
          super().__init__()
          self.shared_text = SharedText()
          self.Delta = SimpleDeltaClient()

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
          

class SimpleDeltaClient:
    def __init__(self):
        self.HOST, self.PORT = "localhost", 2137
        self.sock = None

        try:
             self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
             self.sock.connect((self.HOST, self.PORT))
             
        except Exception as e:
             print(e)
        pass





app = TestApp()
app.run()
