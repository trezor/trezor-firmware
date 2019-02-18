from micropython import const

from trezor import loop, res, ui
from trezor.ui import Widget
from trezor.ui.button import BTN_ACTIVE, BTN_CLICKED, Button
from trezor.ui.loader import Loader

if __debug__:
    from apps.debug import confirm_signal

CONFIRMED = const(1)
CANCELLED = const(2)
DEFAULT_CONFIRM = res.load(ui.ICON_CONFIRM)
DEFAULT_CANCEL = res.load(ui.ICON_CANCEL)


class ConfirmDialog(Widget):
    def __init__(
        self,
        content,
        confirm=DEFAULT_CONFIRM,
        cancel=DEFAULT_CANCEL,
        confirm_style=ui.BTN_CONFIRM,
        cancel_style=ui.BTN_CANCEL,
    ):
        self.content = content
        if cancel is not None:
            self.confirm = Button(ui.grid(9, n_x=2), confirm, style=confirm_style)
            self.cancel = Button(ui.grid(8, n_x=2), cancel, style=cancel_style)
        else:
            self.confirm = Button(ui.grid(4, n_x=1), confirm, style=confirm_style)
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
        if __debug__:
            return await loop.spawn(super().__iter__(), self.content, confirm_signal)
        else:
            return await loop.spawn(super().__iter__(), self.content)


_STARTED = const(-1)
_STOPPED = const(-2)


class HoldToConfirmDialog(Widget):
    def __init__(
        self,
        content,
        hold="Hold to confirm",
        button_style=ui.BTN_CONFIRM,
        loader_style=ui.LDR_DEFAULT,
    ):
        self.content = content
        self.button = Button(ui.grid(4, n_x=1), hold, style=button_style)
        self.loader = Loader(style=loader_style)

        if content.__class__.__iter__ is not Widget.__iter__:
            raise TypeError(
                "HoldToConfirmDialog does not support widgets with custom event loop"
            )

    def taint(self):
        super().taint()
        self.button.taint()
        self.content.taint()

    def render(self):
        self.button.render()
        if not self.loader.is_active():
            self.content.render()

    def touch(self, event, pos):
        button = self.button
        was_active = button.state == BTN_ACTIVE
        button.touch(event, pos)
        is_active = button.state == BTN_ACTIVE
        if is_active and not was_active:
            ui.display.clear()
            self.loader.start()
            return _STARTED
        if was_active and not is_active:
            if self.loader.stop():
                return CONFIRMED
            else:
                return _STOPPED

    async def __iter__(self):
        result = None
        while result is None or result < 0:  # _STARTED or _STOPPED
            if self.loader.is_active():
                if __debug__:
                    result = await loop.spawn(
                        self.loader, super().__iter__(), confirm_signal
                    )
                else:
                    result = await loop.spawn(self.loader, super().__iter__())
            else:
                self.content.taint()
                if __debug__:
                    result = await loop.spawn(super().__iter__(), confirm_signal)
                else:
                    result = await super().__iter__()
        return result
