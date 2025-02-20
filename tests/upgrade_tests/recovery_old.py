from typing import TYPE_CHECKING

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def _enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    typed_word = word[:4]
    for coords in buttons.type_word(typed_word, is_slip39=is_slip39):
        debug.click(coords)
        debug.read_layout(wait=False)

    debug.click(buttons.CONFIRM_WORD)
    return debug.read_layout(wait=True)


def confirm_recovery(debug: "DebugLink") -> None:
    debug.click(buttons.OK)
    debug.read_layout(wait=True)


def select_number_of_words(debug: "DebugLink", num_of_words: int = 20) -> None:
    debug.click(buttons.OK)
    debug.read_layout(wait=True)

    # click the number
    coords_map = {
        12: buttons.grid34(0, 2),
        18: buttons.grid34(1, 2),
        20: buttons.grid34(2, 2),
        24: buttons.grid34(1, 3),
        33: buttons.grid34(2, 3),
    }
    coords = coords_map.get(num_of_words)
    debug.click(coords)
    debug.read_layout(wait=True)


def enter_share(debug: "DebugLink", share: str) -> "LayoutContent":
    debug.click(buttons.OK)
    for word in share.split(" "):
        _enter_word(debug, word, is_slip39=True)

    return debug.read_layout(wait=True)
