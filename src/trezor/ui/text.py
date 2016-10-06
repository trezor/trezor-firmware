from micropython import const
from trezor import ui

TEXT_HEADER_HEIGHT = const(32)
TEXT_LINE_HEIGHT = const(23)
TEXT_MARGIN_LEFT = const(10)


class Text:

    def __init__(self, header, icon, *content):
        self.header = header
        self.icon = icon
        self.content = content

    def render(self):
        offset = TEXT_LINE_HEIGHT
        offset += TEXT_HEADER_HEIGHT
        style = ui.NORMAL
        ui.header(self.header, self.icon, ui.BLACK, ui.LIGHT_GREEN)
        for item in self.content:
            if isinstance(item, str):
                ui.display.text(TEXT_MARGIN_LEFT, offset,
                                item, style, ui.WHITE, ui.BLACK)
                offset += TEXT_LINE_HEIGHT
            else:
                style = item

    def send(self, event, pos):
        pass
