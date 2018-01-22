from micropython import const
from trezor import ui

TEXT_HEADER_HEIGHT = const(48)
TEXT_LINE_HEIGHT = const(26)
TEXT_MARGIN_LEFT = const(14)


class Text(ui.Widget):

    def __init__(self, header_text, header_icon, *content, icon_color=ui.ORANGE_ICON):
        self.header_text = header_text
        self.header_icon = header_icon
        self.icon_color = icon_color
        self.content = content

    def render(self):
        offset_x = TEXT_MARGIN_LEFT
        offset_y = TEXT_LINE_HEIGHT + TEXT_HEADER_HEIGHT
        style = ui.NORMAL
        fg = ui.FG
        bg = ui.BG
        ui.header(self.header_text, self.header_icon, ui.TITLE_GREY, ui.BG, self.icon_color)

        def process(eitem):
            nonlocal offset_y
            nonlocal style
            nonlocal fg
            if isinstance(eitem, str):
                ui.display.text(offset_x, offset_y, eitem, style, fg, bg)
                offset_y += TEXT_LINE_HEIGHT
            elif isinstance(eitem, (tuple, list, dict, set)):
                for i in eitem:
                    process(i)
            elif eitem == ui.MONO or eitem == ui.NORMAL or eitem == ui.BOLD:
                style = eitem
            else:
                fg = eitem

        for item in self.content:
            process(item)
