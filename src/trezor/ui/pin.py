from . import display, clear
from trezor import ui, loop
from trezor.crypto import random
from .button import Button, BTN_CLICKED
from .button import CONFIRM_BUTTON, CONFIRM_BUTTON_ACTIVE
from .button import CANCEL_BUTTON, CANCEL_BUTTON_ACTIVE


def digit_area(i):
    width = const(80)
    height = const(48)
    x = (i % 3) * width
    y = (i // 3) * height
    return (x, y + 48, width, height)  # 48px is offset of input line


def generate_digits():
    digits = list(range(1, 10))  # 1-9
    random.shuffle(digits)
    return digits


class PinMatrix():

    def __init__(self, label='Enter PIN', pin=''):
        self.label = label
        self.pin = pin
        self.clear_button = Button((240 - 35, 5, 30, 30), 'CLEAR')
        self.buttons = [Button(digit_area(i), str(d))
                        for i, d in enumerate(generate_digits())]

    def render(self):

        header = ''.join(['*' for _ in self.pin]) if self.pin else self.label

        # clear canvas under input line
        display.bar(48, 0, 144, 48, ui.BLACK)

        # input line with a header
        display.text_center(120, 30, header, ui.BOLD, ui.GREY, ui.BLACK)

        # render clear button
        if self.pin:
            self.clear_button.render()

        # pin matrix buttons
        for btn in self.buttons:
            btn.render()

        # vertical border bars
        display.bar(79, 48, 2, 143, ui.blend(ui.BLACK, ui.WHITE, 0.25))
        display.bar(158, 48, 2, 143, ui.blend(ui.BLACK, ui.WHITE, 0.25))

        # horizontal border bars
        display.bar(0, 95, 240, 2, ui.blend(ui.BLACK, ui.WHITE, 0.25))
        display.bar(0, 142, 240, 2, ui.blend(ui.BLACK, ui.WHITE, 0.25))

    def send(self, event, pos):
        if self.clear_button.send(event, pos) == BTN_CLICKED:
            self.pin = ''
            self.label = 'Enter PIN'
            display.bar(240 - 48, 0, 48, 42, ui.BLACK)


        for btn in self.buttons:
            if btn.send(event, pos) == BTN_CLICKED:
                self.pin += btn.text
