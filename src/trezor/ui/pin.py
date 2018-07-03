from micropython import const

from trezor import ui
from trezor.crypto import random
from trezor.ui import display
from trezor.ui.button import BTN_CLICKED, Button


def digit_area(i):
    if i == 9:  # 0-position
        i = 10  # display it in the middle
    return ui.grid(i + 3)  # skip the first line


def generate_digits():
    digits = list(range(0, 10))  # 0-9
    random.shuffle(digits)
    return digits


class PinMatrix(ui.Widget):
    def __init__(self, label, pin="", maxlength=9):
        self.label = label
        self.pin = pin
        self.maxlength = maxlength
        self.digits = generate_digits()

        # we lay out the buttons top-left to bottom-right, but the order of the
        # digits is defined as bottom-left to top-right (on numpad)
        reordered_digits = self.digits[6:] + self.digits[3:6] + self.digits[:3]

        self.pin_buttons = [
            Button(digit_area(i), str(d)) for i, d in enumerate(reordered_digits)
        ]
        self.onchange = None

    def render(self):
        # clear canvas under input line
        display.bar(0, 0, ui.WIDTH, 45, ui.BG)

        if self.pin:
            # input line with pin
            l = len(self.pin)
            y = const(20)
            size = const(10)
            padding = const(14)
            box_w = const(240)
            x = (box_w - l * padding) // 2
            for i in range(0, l):
                ui.display.bar_radius(x + i * padding, y, size, size, ui.GREY, ui.BG, 4)
        else:
            # input line with header label
            display.text_center(ui.WIDTH // 2, 36, self.label, ui.BOLD, ui.GREY, ui.BG)

        # pin matrix buttons
        for btn in self.pin_buttons:
            btn.render()

    def touch(self, event, pos):
        for btn in self.pin_buttons:
            if btn.touch(event, pos) == BTN_CLICKED:
                if len(self.pin) < self.maxlength:
                    self.change(self.pin + btn.content)
                break

    def change(self, pin):
        self.pin = pin
        for btn in self.pin_buttons:
            if len(self.pin) == self.maxlength:
                btn.disable()
            else:
                btn.enable()
        if self.onchange:
            self.onchange()
