from micropython import const

from trezor import loop, ui
from trezor.ui import Widget
from trezor.ui.button import BTN_CLICKED, Button

DEVICE = const(0)
HOST = const(1)


class EntrySelector(Widget):
    def __init__(self, content):
        self.content = content
        self.device = Button(ui.grid(8, n_y=4, n_x=4, cells_x=4), "Device")
        self.host = Button(ui.grid(12, n_y=4, n_x=4, cells_x=4), "Host")

    def render(self):
        self.device.render()
        self.host.render()

    def touch(self, event, pos):
        if self.device.touch(event, pos) == BTN_CLICKED:
            return DEVICE
        if self.host.touch(event, pos) == BTN_CLICKED:
            return HOST

    async def __iter__(self):
        return await loop.spawn(super().__iter__(), self.content)
