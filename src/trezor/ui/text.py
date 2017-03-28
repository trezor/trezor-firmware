from micropython import const
from trezor import ui

TEXT_HEADER_HEIGHT = const(32)
TEXT_LINE_HEIGHT = const(23)
TEXT_MARGIN_LEFT = const(10)


class Text(ui.Widget):

    def __init__(self, header_text, header_icon, *content):
        self.header_text = header_text
        self.header_icon = header_icon
        self.content = content

    def render(self):
        offset_x = TEXT_MARGIN_LEFT
        offset_y = TEXT_LINE_HEIGHT + TEXT_HEADER_HEIGHT
        style = ui.NORMAL
        fg = ui.WHITE
        bg = ui.BLACK
        ui.header(self.header_text, self.header_icon, ui.GREEN, ui.BLACK)

        for item in self.content:
            if isinstance(item, str):
                ui.display.text(offset_x, offset_y, item, style, fg, bg)
                offset_y += TEXT_LINE_HEIGHT
            elif item == ui.MONO or item == ui.NORMAL or item == ui.BOLD:
                style = item
            else:
                fg = item

    def send(self, event, pos):
        pass


class RecoveryWordText(ui.Widget):

    def __init__(self, number, word):
        self.number = ('%d.' % number)
        self.word = word

    def render(self):
        offset_y = 96
        style = ui.BOLD
        fg = ui.WHITE
        bg = ui.BLACKISH
        ui.display.bar(0, offset_y - TEXT_LINE_HEIGHT, 240, TEXT_LINE_HEIGHT + 10, bg)
        ui.display.text(TEXT_MARGIN_LEFT, offset_y, self.number, style, fg, bg)
        if len(self.number) < 3:
            ui.display.text(TEXT_MARGIN_LEFT + 20, offset_y, self.word, style, fg, bg)
        else:
            ui.display.text(TEXT_MARGIN_LEFT + 30, offset_y, self.word, style, fg, bg)

    def send(self, event, pos):
        pass
