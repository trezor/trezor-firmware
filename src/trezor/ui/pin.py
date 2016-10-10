from micropython import const
from trezor.crypto import random
from trezor import ui, res
from .button import Button, BTN_CLICKED, CLEAR_BUTTON, CLEAR_BUTTON_ACTIVE
from . import display


def digit_area(i):
    width = const(80)
    height = const(48)
    x = (i % 3) * width
    y = (i // 3) * height
    return (x, y + 48, width - 1, height - 1)  # 48px is offset of input line / -1px is due to corner bug of overlaying elements


def generate_digits():
    digits = list(range(1, 10))  # 1-9
    random.shuffle(digits)
    return digits


class PinMatrix():

    def __init__(self, label='Enter PIN', pin=''):
        self.label = label
        self.pin = pin
        self.clear_button = Button((240 - 35, 5, 30, 30),
                                   res.load('trezor/res/pin_close.toig'),
                                   normal_style=CLEAR_BUTTON,
                                   active_style=CLEAR_BUTTON_ACTIVE)
        self.pin_buttons = [Button(digit_area(i), str(d))
                            for i, d in enumerate(generate_digits())]

    def render(self):

        header = '*' * len(self.pin) if self.pin else self.label

        # clear canvas under input line
        display.bar(0, 0, 205, 48, ui.BLACK)

        # input line with a header
        display.text_center(120, 30, header, ui.BOLD, ui.GREY, ui.BLACK)

        # render clear button
        if self.pin:
            self.clear_button.render()
        else:
            display.bar(240 - 48, 0, 48, 42, ui.BLACK)

        # pin matrix buttons
        for btn in self.pin_buttons:
            btn.render()

        # vertical border bars
        # display.bar(79, 48, 2, 143, ui.blend(ui.BLACK, ui.WHITE, 0.25))
        # display.bar(158, 48, 2, 143, ui.blend(ui.BLACK, ui.WHITE, 0.25))

        # horizontal border bars
        # display.bar(0, 95, 240, 2, ui.blend(ui.BLACK, ui.WHITE, 0.25))
        # display.bar(0, 142, 240, 2, ui.blend(ui.BLACK, ui.WHITE, 0.25))

    def send(self, event, pos):
        if self.clear_button.send(event, pos) == BTN_CLICKED:
            self.pin = ''
        for btn in self.pin_buttons:
            if btn.send(event, pos) == BTN_CLICKED:
                if len(self.pin) < 9:
                    self.pin += btn.content
