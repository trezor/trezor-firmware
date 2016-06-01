from trezor import loop
from trezor.crypto import random
from .button import Button, BTN_CLICKED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE


def digit_area(i):
    width = const(80)
    height = const(60)
    x = (i % 3) * width
    y = (i // 3) * height
    return (x, y, width, height)


def generate_digits():
    digits = list(range(1, 10))  # 1-9
    random.shuffle(digits)
    return digits


class PinMatrix():

    def __init__(self, pin=''):
        self.pin = pin
        self.buttons = [Button(digit_area(i), str(d))
                        for i, d in enumerate(generate_digits())]

    def render(self):
        for btn in self.buttons:
            btn.render()

    def send(self, event, pos):
        for btn in self.buttons:
            if btn.send(event, pos) == BTN_CLICKED:
                self.pin += btn.text
