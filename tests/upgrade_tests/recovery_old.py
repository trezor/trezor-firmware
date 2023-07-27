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

    return debug.click(buttons.CONFIRM_WORD, wait=True)


def confirm_recovery(debug: "DebugLink") -> None:
    debug.click(buttons.OK, wait=True)


def select_number_of_words(
    debug: "DebugLink", num_of_words: int = 20, wait: bool = True
) -> None:
    if wait:
        debug.wait_layout()
    debug.click(buttons.OK, wait=True)

    # click the number
    word_option_offset = 6
    word_options = (12, 18, 20, 24, 33)
    index = word_option_offset + word_options.index(
        num_of_words
    )  # raises if num of words is invalid
    coords = buttons.grid34(index % 3, index // 3)
    debug.click(coords, wait=True)


def enter_share(
    debug: "DebugLink", share: str, is_first: bool = True
) -> "LayoutContent":
    layout = debug.click(buttons.OK, wait=True)
    for word in share.split(" "):
        layout = _enter_word(debug, word, is_slip39=True)
    return layout
