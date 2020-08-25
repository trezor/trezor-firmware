from micropython import const

from trezor import res, ui
from trezor.ui import display, style

TEXT_HEADER_HEIGHT = const(48)
TEXT_LINE_HEIGHT = const(26)
TEXT_LINE_HEIGHT_HALF = const(13)
TEXT_MARGIN_LEFT = const(14)
TEXT_MAX_LINES = const(5)


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
