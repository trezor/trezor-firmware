from micropython import const
from trezor import loop
from .button import Button, BTN_CLICKED, BTN_STARTED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE
from .loader import Loader


CONFIRMED = const(1)
CANCELLED = const(2)


class ConfirmDialog():

    def __init__(self, content=None, confirm='Confirm', cancel='Cancel'):
        self.content = content
        self.confirm = Button((121, 240 - 48, 119, 48), confirm,
                              normal_style=CONFIRM_BUTTON,
                              active_style=CONFIRM_BUTTON_ACTIVE)
        self.cancel = Button((0, 240 - 48, 119, 48), cancel,
                             normal_style=CANCEL_BUTTON,
                             active_style=CANCEL_BUTTON_ACTIVE)

    def render(self):
        if self.content is not None:
            self.content.render()
        self.confirm.render()
        self.cancel.render()

    def send(self, event, pos):
        if self.confirm.send(event, pos) == BTN_CLICKED:
            return CONFIRMED
        if self.cancel.send(event, pos) == BTN_CLICKED:
            return CANCELLED
        if self.content is not None:
            return self.content.send(event, pos)

    def __iter__(self):
        while True:
            self.render()
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result


class HoldToConfirmDialog():

    def __init__(self, button, content=None, *args, **kwargs):
        self.button = button
        self.content = content
        self.loader = Loader(*args, **kwargs)

    def render(self):
        if self.loader.is_active():
            self.loader.render()
        elif self.content is not None:
            self.content.render()
        self.button.render()

    def send(self, event, pos):
        button = self.button
        was_started = button.state & BTN_STARTED
        button.send(event, pos)
        is_started = button.state & BTN_STARTED
        if is_started:
            if not was_started:
                self.loader.start()
        else:
            if was_started:
                if self.loader.stop():
                    return CONFIRMED
        if self.content is not None:
            return self.content.send(event, pos)

    async def __iter__(self):
        await loop.Wait([self._render_loop(),
                         self._event_loop()])

    def _render_loop(self):
        RENDER_DELAY = const(1000000 // 60)
        while True:
            self.render()
            yield loop.Sleep(RENDER_DELAY)

    def _event_loop(self):
        while True:
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result
