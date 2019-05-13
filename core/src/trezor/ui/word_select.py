from trezor import ui
from trezor.ui.button import Button


class WordSelector(ui.Layout):
    def __init__(self, content):
        self.content = content
        self.w12 = Button(ui.grid(6, n_y=4, n_x=3, cells_y=2), "12")
        self.w12.on_click = self.on_w12
        self.w18 = Button(ui.grid(7, n_y=4, n_x=3, cells_y=2), "18")
        self.w18.on_click = self.on_w18
        self.w24 = Button(ui.grid(8, n_y=4, n_x=3, cells_y=2), "24")
        self.w24.on_click = self.on_w24

    def dispatch(self, event, x, y):
        self.content.dispatch(event, x, y)
        self.w12.dispatch(event, x, y)
        self.w18.dispatch(event, x, y)
        self.w24.dispatch(event, x, y)

    def on_w12(self):
        raise ui.Result(12)

    def on_w18(self):
        raise ui.Result(18)

    def on_w24(self):
        raise ui.Result(24)
