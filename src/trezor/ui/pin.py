from . import button
from trezor import loop


def digit_area(d):
    width = const(80)
    height = const(60)
    x = ((d - 1) % 3) * width
    y = ((d - 1) // 3) * height
    return (x, y, width, height)


PIN_CONFIRMED = const(1)
PIN_CANCELLED = const(2)


class PinDialog():

    def __init__(self, pin=''):
        self.pin = pin
        self.confirm_button = button.Button((0, 240 - 60, 120, 60), 'Confirm',
                                            normal_style=button.CONFIRM_BUTTON,
                                            active_style=button.CONFIRM_BUTTON_ACTIVE)
        self.cancel_button = button.Button((120, 240 - 60, 120, 60), 'Cancel',
                                           normal_style=button.CANCEL_BUTTON,
                                           active_style=button.CANCEL_BUTTON_ACTIVE)
        self.pin_buttons = [button.Button(digit_area(dig), str(dig))
                            for dig in range(1, 10)]

    def render(self):
        for btn in self.pin_buttons:
            btn.render()
        self.confirm_button.render()
        self.cancel_button.render()

    def send(self, event, pos):
        for btn in self.pin_buttons:
            if btn.send(event, pos) is button.BTN_CLICKED:
                self.pin += btn.text
        if self.confirm_button.send(event, pos) is button.BTN_CLICKED:
            return PIN_CONFIRMED
        if self.cancel_button.send(event, pos) is button.BTN_CLICKED:
            return PIN_CANCELLED

    def wait_for_result(self):
        while True:
            self.render()
            event, *pos = yield loop.Select(loop.TOUCH_START,
                                            loop.TOUCH_MOVE,
                                            loop.TOUCH_END)
            result = self.send(event, pos)
            if result is not None:
                return result
