from micropython import const
from trezor import ui

TEXT_HEADER_HEIGHT = const(44)
TEXT_LINE_HEIGHT = const(30)
TEXT_MARGIN_LEFT = const(10)


class Text:

    def __init__(self, header, *content):
        self.header = header
        self.content = content

    def render(self):
        offset = TEXT_LINE_HEIGHT
        ui.display.text(TEXT_MARGIN_LEFT, offset,
                        self.header, ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
        offset += TEXT_HEADER_HEIGHT
        style = ui.NORMAL
        for item in self.content:
            if isinstance(item, str):
                ui.display.text(TEXT_MARGIN_LEFT, offset,
                                item, style, ui.WHITE, ui.BLACK)
                offset += TEXT_LINE_HEIGHT
            else:
                style = item

    def send(self, event, pos):
        pass
