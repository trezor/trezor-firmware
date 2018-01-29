from micropython import const
from trezor import loop
from trezor import ui
from trezor.ui import Widget
from trezor.ui.button import Button, BTN_CLICKED

_DEVICE = const(0)
_HOST = const(1)


class EntrySelector(Widget):

    def __init__(self, content):
        self.content = content
        self.device = Button(ui.grid(8, n_y=4, n_x=4, cells_x=4), 'Device',
                          normal_style=ui.BTN_KEY,
                          active_style=ui.BTN_KEY_ACTIVE)
        self.host = Button(ui.grid(12, n_y=4, n_x=4, cells_x=4), 'Host',
                          normal_style=ui.BTN_KEY,
                          active_style=ui.BTN_KEY_ACTIVE)

    def render(self):
        self.device.render()
        self.host.render()

    def touch(self, event, pos):
        if self.device.touch(event, pos) == BTN_CLICKED:
            return _DEVICE
        if self.host.touch(event, pos) == BTN_CLICKED:
            return _HOST

    async def __iter__(self):
        return await loop.wait(super().__iter__(), self.content)
