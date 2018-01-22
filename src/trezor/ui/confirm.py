from micropython import const
from trezor import loop
from trezor import ui, res
from trezor.ui import Widget
from trezor.ui.button import Button, BTN_CLICKED, BTN_STARTED, BTN_ACTIVE
from trezor.ui.loader import Loader

CONFIRMED = const(1)
CANCELLED = const(2)
DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)
DEFAULT_CANCEL = res.load(ui.ICON_CLEAR)


class ConfirmDialog(Widget):

    def __init__(self, content, confirm=DEFAULT_CONFIRM, cancel=DEFAULT_CANCEL):
        self.content = content
        if cancel is not None:
            self.confirm = Button(ui.grid(9, n_x=2), confirm,
                                  normal_style=ui.BTN_CONFIRM,
                                  active_style=ui.BTN_CONFIRM_ACTIVE)
            self.cancel = Button(ui.grid(8, n_x=2), cancel,
                                 normal_style=ui.BTN_CANCEL,
                                 active_style=ui.BTN_CANCEL_ACTIVE)
        else:
            self.confirm = Button(ui.grid(4, n_x=1), confirm,
                                  normal_style=ui.BTN_CONFIRM,
                                  active_style=ui.BTN_CONFIRM_ACTIVE)
            self.cancel = None

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
        self.button = Button(ui.grid(4, n_x=1), hold,
                             normal_style=ui.BTN_CONFIRM,
                             active_style=ui.BTN_CONFIRM_ACTIVE)
        self.loader = Loader(*args, **kwargs)

    def render(self):
        self.button.render()

    def touch(self, event, pos):
        button = self.button
        was_started = button.state & BTN_STARTED and button.state & BTN_ACTIVE
        button.touch(event, pos)
        is_started = button.state & BTN_STARTED and button.state & BTN_ACTIVE
        if is_started and not was_started:
            ui.display.clear()
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
