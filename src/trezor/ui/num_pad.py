from trezor import res, ui
from trezor.ui import display
from trezor.ui.button import BTN_CLICKED, Button

ITEMS_PER_PAGE = 10
PLUS_BUTTON_POSITION = 11
BACK_BUTTON_POSITION = 9


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
                elif isinstance(btn.content, bytes):
                    self.page -= 1
                    self._generate_buttons()
                else:
                    return btn.content

    def _generate_buttons(self):
        display.clear()  # we need to clear old buttons
        start = self.start + (ITEMS_PER_PAGE + 1) * self.page - self.page
        end = min(self.end, (ITEMS_PER_PAGE + 1) * (self.page + 1) - self.page)

        digits = list(range(start, end))
        self.buttons = [Button(digit_area(i), str(d)) for i, d in enumerate(digits)]
        if len(digits) == ITEMS_PER_PAGE:
            more = Button(
                digit_area(PLUS_BUTTON_POSITION), str(end) + "+", style=ui.BTN_KEY_DARK
            )
            self.buttons.append(more)
            # move the tenth button to its proper place and make place for the back button
            self.buttons[BACK_BUTTON_POSITION].area = digit_area(
                BACK_BUTTON_POSITION + 1
            )

        back = Button(
            digit_area(BACK_BUTTON_POSITION),
            res.load(ui.ICON_BACK),
            style=ui.BTN_KEY_DARK,
        )
        if self.page == 0:
            back.disable()
        self.buttons.append(back)
