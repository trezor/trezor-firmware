from trezor import ui

TEXT_HEADER_HEIGHT = const(44)
TEXT_LINE_HEIGHT = const(30)
TEXT_MARGIN_LEFT = const(10)


class Text:

    def __init__(self, header, *lines):
        self.header = header
        self.lines = lines

    def render(self):
        offset = TEXT_LINE_HEIGHT
        ui.display.text(TEXT_MARGIN_LEFT, offset,
                        self.header, ui.BOLD, ui.LIGHT_GREEN, ui.BLACK)
        offset += TEXT_HEADER_HEIGHT
        for style, line in self.lines:
            ui.display.text(TEXT_MARGIN_LEFT, offset,
                            line, style, ui.WHITE, ui.BLACK)
            offset += TEXT_LINE_HEIGHT

    def send(self, event, pos):
        pass
