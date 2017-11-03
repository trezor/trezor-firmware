from micropython import const
from trezor import loop
from trezor import ui, res
from trezor.ui import Widget
from trezor.ui.button import Button, BTN_CLICKED, BTN_STARTED, BTN_ACTIVE

W12 = '12'
W15 = '15'
W18 = '18'
W24 = '24'

class WordSelector(Widget):

    def __init__(self, content):
        self.content = content
        self.w12 = Button((6, 135, 114, 51), W12,
                          normal_style=ui.BTN_KEY,
                          active_style=ui.BTN_KEY_ACTIVE)
        self.w15 = Button((120, 135, 114, 51), W15,
                          normal_style=ui.BTN_KEY,
                          active_style=ui.BTN_KEY_ACTIVE)
        self.w18 = Button((6, 186, 114, 51), W18,
                          normal_style=ui.BTN_KEY,
                          active_style=ui.BTN_KEY_ACTIVE)
        self.w24 = Button((120, 186, 114, 51), W24,
                          normal_style=ui.BTN_KEY,
                          active_style=ui.BTN_KEY_ACTIVE)

    def render(self):
        self.w12.render()
        self.w15.render()
        self.w18.render()
        self.w24.render()

    def touch(self, event, pos):
        if self.w12.touch(event, pos) == BTN_CLICKED:
            return W12
        if self.w15.touch(event, pos) == BTN_CLICKED:
            return W15
        if self.w18.touch(event, pos) == BTN_CLICKED:
            return W18
        if self.w24.touch(event, pos) == BTN_CLICKED:
            return W24

    async def __iter__(self):
        return await loop.wait(super().__iter__(), self.content)


_STARTED = const(-1)
_STOPPED = const(-2)



