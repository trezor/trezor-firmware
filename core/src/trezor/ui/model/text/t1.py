from micropython import const

from trezor import ui
from trezor.ui import display, style

TEXT_HEADER_HEIGHT = const(13)
TEXT_LINE_HEIGHT = const(9)
TEXT_LINE_HEIGHT_HALF = const(4)
TEXT_MARGIN_LEFT = const(0)
TEXT_MAX_LINES = const(4)


def header(
    title: str,
    icon: str = style.ICON_DEFAULT,
    fg: int = style.FG,
    bg: int = style.BG,
    ifg: int = style.GREEN,
) -> None:
    # icon is ignored
    display.text(0, 7, title, ui.BOLD, fg, bg)
    for x in range(0, ui.WIDTH, 2):
        display.bar(x, 9, 1, 1, ui.FG)
