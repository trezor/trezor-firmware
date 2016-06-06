from . import display
from trezor import ui
from trezor import loop
from trezor.crypto import random
from .button import Button, BTN_CLICKED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE


def digit_area(i):
    width = const(80)
    height = const(48)
    x = (i % 3) * width
    y = (i // 3) * height
    return (x, y + 48, width, height) # 48px is offset of input line


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

        # input line with placeholder (x, y, text, style, fg-c, bg-c)
        display.text_center(120, 20, 'Enter PIN', ui.BOLD, ui.GREY, ui.BLACK)

        # vertical border bars (x, y, w, h, c)
        display.bar(79, 48, 2, 143, ui.blend(ui.BLACK, ui.WHITE, 0.25))
        display.bar(158, 48, 2, 143, ui.blend(ui.BLACK, ui.WHITE, 0.25))

        # horizontal border bars
        display.bar(0, 95, 240, 2, ui.blend(ui.BLACK, ui.WHITE, 0.25))
        display.bar(0, 142, 240, 2, ui.blend(ui.BLACK, ui.WHITE, 0.25))

        # pin matrix buttons
        for btn in self.buttons:
            btn.render()

    def send(self, event, pos):
        for btn in self.buttons:
            if btn.send(event, pos) == BTN_CLICKED:
                self.pin += btn.text
