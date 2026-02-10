from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def _enter_word(debug: "DebugLink", word: str, is_slip39: bool = False) -> None:
    typed_word = word[:4]
    for coords in debug.button_actions.type_word(typed_word, is_slip39=is_slip39):
        debug.click(coords, wait=False)

    debug.click(debug.screen_buttons.mnemonic_confirm(), wait=False)


def confirm_recovery(debug: "DebugLink") -> None:
    debug.click(debug.screen_buttons.ok())


def select_number_of_words(
    debug: "DebugLink", tag_version: tuple | None, num_of_words: int = 20
) -> None:
    if "SelectWordCount" not in debug.read_layout().all_components():
        debug.click(debug.screen_buttons.ok())
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


def enter_share(debug: "DebugLink", share: str) -> "LayoutContent":
    layout = debug.read_layout()
    # Check for both MnemonicKeyboard (newer) and Slip39Keyboard (older firmware)
    # For old firmware, tokens may be plain string (not JSON), so check json_str directly
    while ("MnemonicKeyboard" not in layout.all_components() and "Slip39Keyboard" not in layout.all_components() and
           "MnemonicKeyboard" not in layout.json_str and "Slip39Keyboard" not in layout.json_str):
        debug.click(debug.screen_buttons.ok())
        layout = debug.read_layout()
    
    # Fast entry of all 20 words
    for word in share.split(" "):
        _enter_word(debug, word, is_slip39=True)
    
    # After all words entered, poll for recovery status to appear
    import time
    for _ in range(10):  # max 1 second total
        time.sleep(0.1)
        layout = debug.read_layout()
        # Check if we left the keyboard
        if ("MnemonicKeyboard" not in layout.all_components() and 
            "Slip39Keyboard" not in layout.all_components() and
            "MnemonicKeyboard" not in layout.json_str and 
            "Slip39Keyboard" not in layout.json_str):
            break
    
    return layout
