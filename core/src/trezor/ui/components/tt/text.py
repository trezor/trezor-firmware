from micropython import const

from trezor import res, ui
from trezor.ui import display, style

from ..common.text import (  # noqa: F401
    BR,
    BR_HALF,
    TEXT_MAX_LINES,
    TextBase,
    render_text,
)

if False:
    from typing import List
    from ..common.text import TextContent


def header(
    title: str,
    icon: str = style.ICON_DEFAULT,
    fg: int = style.FG,
    bg: int = style.BG,
    ifg: int = style.GREEN,
) -> None:
    if icon is not None:
        display.icon(14, 15, res.load(icon), ifg, bg)
    display.text(44, 35, title, ui.BOLD, fg, bg)


class Text(TextBase):
    def __init__(
        self,
        header_text: str,
        header_icon: str = ui.ICON_DEFAULT,
        icon_color: int = ui.ORANGE_ICON,
        max_lines: int = TEXT_MAX_LINES,
        new_lines: bool = True,
    ):
        super().__init__()
        self.header_text = header_text  # type: str
        self.header_icon = header_icon
        self.icon_color = icon_color
        self.max_lines = max_lines
        self.new_lines = new_lines
        self.content = []  # type: List[TextContent]

    def on_render(self) -> None:
        if self.repaint:
            header(
                self.header_text,
                self.header_icon,
                ui.TITLE_GREY,
                ui.BG,
                self.icon_color,
            )
            render_text(self.content, self.new_lines, self.max_lines)
            self.repaint = False


LABEL_LEFT = const(0)
LABEL_CENTER = const(1)
LABEL_RIGHT = const(2)


class Label(ui.Component):
    def __init__(
        self,
        area: ui.Area,
        content: str,
        align: int = LABEL_LEFT,
        style: int = ui.NORMAL,
    ) -> None:
        self.area = area
        self.content = content
        self.align = align
        self.style = style
        self.repaint = True

    def on_render(self) -> None:
        if self.repaint:
            align = self.align
            ax, ay, aw, ah = self.area
            ui.display.bar(ax, ay, aw, ah, ui.BG)
            tx = ax + aw // 2
            ty = ay + ah // 2 + 8
            if align is LABEL_LEFT:
                ui.display.text(tx, ty, self.content, self.style, ui.FG, ui.BG)
            elif align is LABEL_CENTER:
                ui.display.text_center(tx, ty, self.content, self.style, ui.FG, ui.BG)
            elif align is LABEL_RIGHT:
                ui.display.text_right(tx, ty, self.content, self.style, ui.FG, ui.BG)
            self.repaint = False

    if __debug__:

        def read_content(self) -> List[str]:
            return [self.content]


def text_center_trim_left(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[-i:], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[-text_length:], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
    x += ELLIPSIS_WIDTH
    ui.display.text(x, y, text[-text_length:], font, ui.FG, ui.BG)


def text_center_trim_right(
    x: int, y: int, text: str, font: int = ui.NORMAL, width: int = ui.WIDTH - 16
) -> None:
    if ui.display.text_width(text, font) <= width:
        ui.display.text_center(x, y, text, font, ui.FG, ui.BG)
        return

    ELLIPSIS_WIDTH = ui.display.text_width("...", ui.BOLD)
    if width < ELLIPSIS_WIDTH:
        return

    text_length = 0
    for i in range(1, len(text)):
        if ui.display.text_width(text[:i], font) + ELLIPSIS_WIDTH > width:
            text_length = i - 1
            break

    text_width = ui.display.text_width(text[:text_length], font)
    x -= (text_width + ELLIPSIS_WIDTH) // 2
    ui.display.text(x, y, text[:text_length], font, ui.FG, ui.BG)
    x += text_width
    ui.display.text(x, y, "...", ui.BOLD, ui.GREY, ui.BG)
