from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static


class TestApp(App):
        BINDINGS = [("b", "toggle_dark", "Toggle dark mode"),
                ("space", "turn_sort", "Turn on sorting"),
                ("esc", "quit", "Quit TUI"),
                ("w,up,k", "test_key(0)", "Move Up"),
                ("s,down,j", "test_key(1)", "Move Down"),
                ("a,left,h", "test_key(2)", "Move Left"),
                ("d,right,l", "test_key(3)", "Move Right")]
        
        def __init__(self):
            super().__init__()
            self.display_text = "Press certain key"

        def on_mount(self):
             self.set_interval(0.5, self.update_text)

        
        def compose(self) -> ComposeResult:
            yield Header()
            yield Footer()
            yield Static(self.display_text)

        def update_text(self):
             self.update(self.display_text)

        def action_test_key(self, num):
             self.display_text = str(num)
             

app = TestApp()
app.run()
