from micropython import const

from trezor import loop, ui
from trezor.ui import Widget
from trezor.ui.button import BTN_CLICKED, Button

if __debug__:
    from apps.debug import input_signal


_W12 = const(12)
_W18 = const(18)
_W24 = const(24)


class WordSelector(Widget):
    def __init__(self, content):
        self.content = content
        self.w12 = Button(
            ui.grid(6, n_y=4, n_x=3, cells_y=2), str(_W12), style=ui.BTN_KEY
        )
        self.w18 = Button(
            ui.grid(7, n_y=4, n_x=3, cells_y=2), str(_W18), style=ui.BTN_KEY
        )
        self.w24 = Button(
            ui.grid(8, n_y=4, n_x=3, cells_y=2), str(_W24), style=ui.BTN_KEY
        )

    def render(self):
        self.w12.render()
        self.w18.render()
        self.w24.render()

    def touch(self, event, pos):
        if self.w12.touch(event, pos) == BTN_CLICKED:
            return _W12
        if self.w18.touch(event, pos) == BTN_CLICKED:
            return _W18
        if self.w24.touch(event, pos) == BTN_CLICKED:
            return _W24

    async def __iter__(self):
        if __debug__:
            result = await loop.spawn(super().__iter__(), self.content, input_signal)
            if isinstance(result, str):
                return int(result)
            else:
                return result
        else:
            return await loop.spawn(super().__iter__(), self.content)
