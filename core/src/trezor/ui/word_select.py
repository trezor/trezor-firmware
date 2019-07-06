from trezor import ui
from trezor.ui.button import Button

# todo improve?


class WordSelector(ui.Layout):
    def __init__(self, content):
        self.content = content
        self.w12 = Button(ui.grid(6, n_y=4), "12")
        self.w12.on_click = self.on_w12
        self.w18 = Button(ui.grid(7, n_y=4), "18")
        self.w18.on_click = self.on_w18
        self.w20 = Button(ui.grid(8, n_y=4), "20")
        self.w20.on_click = self.on_w20
        self.w24 = Button(ui.grid(9, n_y=4), "24")
        self.w24.on_click = self.on_w24
        self.w33 = Button(ui.grid(10, n_y=4), "33")
        self.w33.on_click = self.on_w33

    def dispatch(self, event, x, y):
        self.content.dispatch(event, x, y)
        self.w12.dispatch(event, x, y)
        self.w18.dispatch(event, x, y)
        self.w20.dispatch(event, x, y)
        self.w24.dispatch(event, x, y)
        self.w33.dispatch(event, x, y)

    def on_w12(self):
        raise ui.Result(12)

    def on_w18(self):
        raise ui.Result(18)

    def on_w20(self):
        raise ui.Result(20)

    def on_w24(self):
        raise ui.Result(24)

    def on_w33(self):
        raise ui.Result(33)
