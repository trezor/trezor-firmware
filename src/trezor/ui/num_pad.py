from trezor import ui
from trezor.ui import display
from trezor.ui.button import BTN_CLICKED, Button

ITEMS_PER_PAGE = 11


def digit_area(i):
    return ui.grid(i + 3)  # skip the first line


class NumPad(ui.Widget):
    def __init__(self, label: str, start: int, end: int):
        """
        Generates a numpad with numbers from `start` to `end` excluding.
        """
        self.label = label
        self.start = start
        self.end = end
        self.page = 0

        self._generate_buttons()

    def render(self):
        for btn in self.buttons:
            btn.render()

        # header label
        display.text_center(ui.WIDTH // 2, 36, self.label, ui.BOLD, ui.GREY, ui.BG)

    def touch(self, event, pos):
        for btn in self.buttons:
            if btn.touch(event, pos) == BTN_CLICKED:
                if "+" in btn.content:
                    self.page += 1
                    self._generate_buttons()
                else:
                    return btn.content

    def _generate_buttons(self):
        display.clear()  # we need to clear old buttons
        start = self.start + (ITEMS_PER_PAGE + 1) * self.page - self.page
        end = min(self.end, (ITEMS_PER_PAGE + 1) * (self.page + 1) - self.page)
        digits = list(range(start, end))
        if len(digits) == ITEMS_PER_PAGE:
            digits.append(str(end) + "+")
        self.buttons = [Button(digit_area(i), str(d)) for i, d in enumerate(digits)]
