from .button import Button, BTN_CLICKED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE
from trezor import loop


CONFIRMED = const(1)
CANCELLED = const(2)


class ConfirmDialog():

    def __init__(self, content=None, confirm='Confirm', cancel='Cancel'):
        self.content = content
        self.confirm = Button((0, 240 - 60, 120, 60), confirm,
                              normal_style=CONFIRM_BUTTON,
                              active_style=CONFIRM_BUTTON_ACTIVE)
        self.cancel = Button((120, 240 - 60, 120, 60), cancel,
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

    def wait(self):
        while True:
            self.render()
            event, *pos = yield loop.Select(loop.TOUCH)
            result = self.send(event, pos)
            if result is not None:
                return result
