from micropython import const
from trezor import loop
from trezor.ui import Widget
from .button import Button, BTN_CLICKED, BTN_STARTED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE
from .loader import Loader

CONFIRMED = const(1)
CANCELLED = const(2)


class ConfirmDialog(Widget):

    def __init__(self, content, confirm='Confirm', cancel='Cancel'):
        self.content = content
        if cancel is not None:
            self.confirm = Button((121, 240 - 48, 119, 48), confirm,
                                  normal_style=CONFIRM_BUTTON,
                                  active_style=CONFIRM_BUTTON_ACTIVE)
            self.cancel = Button((0, 240 - 48, 119, 48), cancel,
                                 normal_style=CANCEL_BUTTON,
                                 active_style=CANCEL_BUTTON_ACTIVE)
        else:
            self.cancel = None
            self.confirm = Button((0, 240 - 48, 240, 48), confirm,
                                  normal_style=CONFIRM_BUTTON,
                                  active_style=CONFIRM_BUTTON_ACTIVE)

    def render(self):
        self.confirm.render()
        if self.cancel is not None:
            self.cancel.render()

    def touch(self, event, pos):
        if self.confirm.touch(event, pos) == BTN_CLICKED:
            return CONFIRMED

        if self.cancel is not None:
            if self.cancel.touch(event, pos) == BTN_CLICKED:
                return CANCELLED

    async def __iter__(self):
        return await loop.wait(super().__iter__(), self.content)


_STARTED = const(-1)
_STOPPED = const(-2)


class HoldToConfirmDialog(Widget):

    def __init__(self, content, hold='Hold to confirm', *args, **kwargs):
        self.content = content
        self.button = Button((0, 240 - 48, 240, 48), hold,
                             normal_style=CONFIRM_BUTTON,
                             active_style=CONFIRM_BUTTON_ACTIVE)
        self.loader = Loader(*args, **kwargs)

    def render(self):
        self.button.render()

    def touch(self, event, pos):
        button = self.button
        was_started = button.state & BTN_STARTED
        button.touch(event, pos)
        is_started = button.state & BTN_STARTED
        if is_started and not was_started:
            self.loader.start()
            return _STARTED
        if was_started and not is_started:
            if self.loader.stop():
                return CONFIRMED
            else:
                return _STOPPED

    async def __iter__(self):
        result = None
        while result is None or result < 0:  # _STARTED or _STOPPED
            if self.loader.is_active():
                content_loop = self.loader
            else:
                content_loop = self.content
            confirm_loop = super().__iter__()  # default loop (render on touch)
            result = await loop.wait(content_loop, confirm_loop)
        return result
