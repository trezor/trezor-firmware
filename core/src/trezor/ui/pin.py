from micropython import const

from trezor import res, ui
from trezor.crypto import random
from trezor.ui import display
from trezor.ui.button import (
    Button,
    ButtonCancel,
    ButtonClear,
    ButtonConfirm,
    ButtonMono,
)


def digit_area(i):
    if i == 9:  # 0-position
        i = 10  # display it in the middle
    return ui.grid(i + 3)  # skip the first line


def generate_digits():
    digits = list(range(0, 10))  # 0-9
    random.shuffle(digits)
    # We lay out the buttons top-left to bottom-right, but the order
    # of the digits is defined as bottom-left to top-right (on numpad).
    return digits[6:] + digits[3:6] + digits[:3]


class PinInput(ui.Control):
    def __init__(self, prompt, subprompt, pin):
        self.prompt = prompt
        self.subprompt = subprompt
        self.pin = pin
        self.repaint = True

    def on_render(self):
        if self.repaint:
            if self.pin:
                self.render_pin()
            else:
                self.render_prompt()
            self.repaint = False

    def render_pin(self):
        display.bar(0, 0, ui.WIDTH, 50, ui.BG)
        count = len(self.pin)
        BOX_WIDTH = const(240)
        DOT_SIZE = const(10)
        PADDING = const(14)
        RENDER_Y = const(20)
        render_x = (BOX_WIDTH - count * PADDING) // 2
        for i in range(0, count):
            display.bar_radius(
                render_x + i * PADDING, RENDER_Y, DOT_SIZE, DOT_SIZE, ui.GREY, ui.BG, 4
            )

    def render_prompt(self):
        display.bar(0, 0, ui.WIDTH, 50, ui.BG)
        if self.subprompt:
            display.text_center(ui.WIDTH // 2, 20, self.prompt, ui.BOLD, ui.GREY, ui.BG)
            display.text_center(
                ui.WIDTH // 2, 46, self.subprompt, ui.NORMAL, ui.GREY, ui.BG
            )
        else:
            display.text_center(ui.WIDTH // 2, 36, self.prompt, ui.BOLD, ui.GREY, ui.BG)


class PinButton(Button):
    def __init__(self, index, digit, matrix):
        self.matrix = matrix
        super().__init__(digit_area(index), str(digit), ButtonMono)

    def on_click(self):
        self.matrix.assign(self.matrix.input.pin + self.content)


CANCELLED = object()


class PinDialog(ui.Layout):
    def __init__(self, prompt, subprompt, allow_cancel=True, maxlength=9):
        self.maxlength = maxlength
        self.input = PinInput(prompt, subprompt, "")

        icon_confirm = res.load(ui.ICON_CONFIRM)
        self.confirm_button = Button(ui.grid(14), icon_confirm, ButtonConfirm)
        self.confirm_button.on_click = self.on_confirm

        icon_back = res.load(ui.ICON_BACK)
        self.reset_button = Button(ui.grid(12), icon_back, ButtonClear)
        self.reset_button.on_click = self.on_reset

        if allow_cancel:
            icon_lock = res.load(ui.ICON_LOCK)
            self.cancel_button = Button(ui.grid(12), icon_lock, ButtonCancel)
            self.cancel_button.on_click = self.on_cancel
        else:
            self.cancel_button = Button(ui.grid(12), "")
            self.cancel_button.disable()

        self.pin_buttons = [
            PinButton(i, d, self) for i, d in enumerate(generate_digits())
        ]

    def dispatch(self, event, x, y):
        for btn in self.pin_buttons:
            btn.dispatch(event, x, y)
        self.input.dispatch(event, x, y)
        self.confirm_button.dispatch(event, x, y)
        if self.input.pin:
            self.reset_button.dispatch(event, x, y)
        else:
            self.cancel_button.dispatch(event, x, y)

    def assign(self, pin):
        if len(pin) > self.maxlength:
            return
        for btn in self.pin_buttons:
            if len(pin) < self.maxlength:
                btn.enable()
            else:
                btn.disable()
        if pin:
            self.reset_button.enable()
            self.cancel_button.disable()
        else:
            self.reset_button.disable()
            self.cancel_button.enable()
        self.input.pin = pin
        self.input.repaint = True

    def on_reset(self):
        self.assign("")

    def on_cancel(self):
        raise ui.Result(CANCELLED)

    def on_confirm(self):
        raise ui.Result(self.input.pin)
