from micropython import const

from trezor import ui
from trezor.ui import display

from ...constants.t1 import TEXT_LINE_HEIGHT

_HEADER_HEIGHT = const(13)


def header(message: str, clear: bool = True) -> None:
    if clear:
        display.bar(0, 0, ui.WIDTH, ui.HEIGHT, ui.BG)
    display.bar(0, 1, ui.WIDTH, _HEADER_HEIGHT - 2, ui.FG)
    display.bar(1, 0, ui.WIDTH - 2, _HEADER_HEIGHT, ui.FG)
    display.text(3, TEXT_LINE_HEIGHT + 1, message, ui.BOLD, ui.BG, ui.FG)
