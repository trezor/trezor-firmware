from typing import TYPE_CHECKING

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def _enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    typed_word = word[:4]
    for coords in buttons.type_word(typed_word, debug.layout_type, is_slip39=is_slip39):
        debug.click(coords)
        debug.read_layout(wait=False)

    debug.click(buttons.CONFIRM_WORD)
    return debug.read_layout(wait=True)


def confirm_recovery(debug: "DebugLink") -> None:
    debug.click(buttons.ok(debug.layout_type))
    debug.read_layout(wait=True)


def select_number_of_words(
    debug: "DebugLink", tag_version: tuple | None, num_of_words: int = 20
) -> None:
    if "SelectWordCount" not in debug.read_layout().all_components():
        debug.click(buttons.ok(debug.layout_type))
        debug.read_layout(wait=True)
    if tag_version is None or tag_version > (2, 8, 8):
        # layout changed after adding the cancel button
        coords_map = {
            12: buttons.grid34(0, 2, debug.layout_type),
            18: buttons.grid34(1, 2, debug.layout_type),
            20: buttons.grid34(2, 2, debug.layout_type),
            24: buttons.grid34(1, 3, debug.layout_type),
            33: buttons.grid34(2, 3, debug.layout_type),
        }
        coords = coords_map.get(num_of_words)
    else:
        word_option_offset = 6
        word_options = (12, 18, 20, 24, 33)
        index = word_option_offset + word_options.index(
            num_of_words
        )  # raises if num of words is invalid
        coords = buttons.grid34(index % 3, index // 3, debug.layout_type)
    debug.click(coords)
    debug.read_layout(wait=True)


def enter_share(debug: "DebugLink", share: str) -> "LayoutContent":
    debug.click(buttons.ok(debug.layout_type))
    for word in share.split(" "):
        _enter_word(debug, word, is_slip39=True)

    return debug.read_layout(wait=True)
