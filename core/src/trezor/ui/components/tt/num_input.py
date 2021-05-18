from trezor import ui

from .button import Button
from .text import LABEL_CENTER, Label


class NumInput(ui.Component):
    def __init__(self, count: int = 5, max_count: int = 16, min_count: int = 1) -> None:
        super().__init__()
        self.count = count
        self.max_count = max_count
        self.min_count = min_count

        self.minus = Button(ui.grid(3), "-")
        self.minus.on_click = self.on_minus  # type: ignore
        self.plus = Button(ui.grid(5), "+")
        self.plus.on_click = self.on_plus  # type: ignore
        self.text = Label(ui.grid(4), "", LABEL_CENTER, ui.BOLD)

        self.edit(count)

    def dispatch(self, event: int, x: int, y: int) -> None:
        self.minus.dispatch(event, x, y)
        self.plus.dispatch(event, x, y)
        self.text.dispatch(event, x, y)

    def on_minus(self) -> None:
        self.edit(self.count - 1)

    def on_plus(self) -> None:
        self.edit(self.count + 1)

    def edit(self, count: int) -> None:
        count = max(count, self.min_count)
        count = min(count, self.max_count)
        if self.count != count:
            self.on_change(count)
        self.count = count
        self.text.content = str(count)
        self.text.repaint = True
        if self.count == self.min_count:
            self.minus.disable()
        else:
            self.minus.enable()
        if self.count == self.max_count:
            self.plus.disable()
        else:
            self.plus.enable()

    def on_change(self, count: int) -> None:
        pass
