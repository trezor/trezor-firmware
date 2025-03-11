from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def _enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    typed_word = word[:4]
    for coords in debug.button_actions.type_word(typed_word, is_slip39=is_slip39):
        debug.click(coords)
        debug.read_layout(wait=False)

    debug.click(debug.screen_buttons.mnemonic_confirm())
    return debug.read_layout(wait=True)


def confirm_recovery(debug: "DebugLink") -> None:
    debug.click(debug.screen_buttons.ok())
    debug.read_layout(wait=True)


def select_number_of_words(
    debug: "DebugLink", tag_version: tuple | None, num_of_words: int = 20
) -> None:
    if "SelectWordCount" not in debug.read_layout().all_components():
        debug.click(debug.screen_buttons.ok())
        debug.read_layout(wait=True)
    if tag_version is None or tag_version > (2, 8, 8):
        # layout changed after adding the cancel button
        coords = debug.screen_buttons.word_count_all_word(num_of_words)
    else:
        word_option_offset = 6
        word_options = (12, 18, 20, 24, 33)
        index = word_option_offset + word_options.index(
            num_of_words
        )  # raises if num of words is invalid
        coords = debug.screen_buttons.grid34(index % 3, index // 3)
    debug.click(coords)
    debug.read_layout(wait=True)


def enter_share(debug: "DebugLink", share: str) -> "LayoutContent":
    debug.click(debug.screen_buttons.ok())
    for word in share.split(" "):
        _enter_word(debug, word, is_slip39=True)

    return debug.read_layout(wait=True)
