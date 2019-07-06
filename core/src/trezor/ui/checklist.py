from micropython import const

from trezor import res, ui
from trezor.ui.text import TEXT_HEADER_HEIGHT, TEXT_LINE_HEIGHT

_CHECKLIST_MAX_LINES = const(5)
_CHECKLIST_OFFSET_X = const(24)
_CHECKLIST_OFFSET_X_ICON = const(0)


class Checklist(ui.Control):
    def __init__(self, title, icon):
        self.title = title
        self.icon = icon
        self.items = []
        self.active = 0
        self.repaint = True

    def add(self, choice):
        self.items.append(choice)

    def select(self, active):
        self.active = active

    def on_render(self):
        if self.repaint:
            ui.header(self.title, self.icon)
            self.render_items()
            self.repaint = False

    def render_items(self):
        offset_x = _CHECKLIST_OFFSET_X
        offset_y = TEXT_HEADER_HEIGHT + TEXT_LINE_HEIGHT
        bg = ui.BG

        for index, item in enumerate(self.items):
            # compute font and color
            if index < self.active:
                font = ui.BOLD
                fg = ui.GREEN
            elif index == self.active:
                font = ui.BOLD
                fg = ui.FG
            else:  # index > self.active
                font = ui.NORMAL
                fg = ui.GREY

            # render item icon
            icon = res.load(ui.ICON_CONFIRM)
            ui.display.icon(0, offset_y - 14, icon, fg, bg)

            # render item text
            if isinstance(item, str):
                ui.display.text(offset_x, offset_y, item, font, fg, bg)
                offset_y += TEXT_LINE_HEIGHT
            else:
                for line in item:
                    ui.display.text(offset_x, offset_y, line, font, fg, bg)
                    offset_y += TEXT_LINE_HEIGHT
