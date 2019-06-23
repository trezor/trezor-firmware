from micropython import const

from trezor import ui
from trezor.ui import text

_CHECKLIST_MAX_LINES = const(5)
_CHECKLIST_OFFSET_X = const(24)


class Checklist(ui.Control):
    def __init__(self, title, icon):
        self.title = title
        self.icon = icon
        self.choices = []
        self.words = []
        self.active = 0
        self.repaint = False

    def add(self, choice):
        self.choices.append(choice)

    def select(self, active):
        self.active = active

    def process(self):
        w = self.words
        w.clear()
        for index, choice in enumerate(self.choices):
            if index < self.active:
                w.append(ui.BOLD)
                w.append(ui.GREEN)
            elif index == self.active:
                w.append(ui.BOLD)
                w.append(ui.FG)
            else:  # index > self.active
                w.append(ui.NORMAL)
                w.append(ui.GREY)
            if isinstance(choice, str):
                w.append(choice)
            else:  # choice is iterable
                w.extend(choice)
            w.append(text.BR)
        self.words = w
        self.repaint = True

    def on_render(self):
        if self.repaint:
            ui.header(self.title, self.icon)
            text.render_text(
                self.words,
                new_lines=False,  # we are adding line breaks manually
                max_lines=_CHECKLIST_MAX_LINES,
                offset_x=_CHECKLIST_OFFSET_X,
            )
            self.repaint = False
