from typing import TYPE_CHECKING

from .. import buttons

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink, LayoutContent


def enter_word(
    debug: "DebugLink", word: str, is_slip39: bool = False
) -> "LayoutContent":
    typed_word = word[:4]
    for coords in buttons.type_word(typed_word, is_slip39=is_slip39):
        debug.click(coords)

    # For BIP39 - double-click on CONFIRM WORD is needed in case the word
    # is not already typed as a whole
    if not is_slip39 and typed_word != word:
        debug.click(buttons.CONFIRM_WORD)
    return debug.click(buttons.CONFIRM_WORD, wait=True)


def confirm_recovery(debug: "DebugLink", legacy_ui: bool = False) -> None:
    layout = debug.wait_layout()
    if legacy_ui:
        layout.str_content.startswith("Recovery mode")
    else:
        assert layout.title() == "RECOVERY MODE"
    debug.click(buttons.OK, wait=True)


def select_number_of_words(
    debug: "DebugLink", num_of_words: int = 20, legacy_ui: bool = False
) -> None:
    layout = debug.read_layout()

    # select number of words
    if legacy_ui:
        assert "Select number of words" in layout.str_content
    else:
        assert "select the number of words" in layout.text_content()

    layout = debug.click(buttons.OK, wait=True)

    if legacy_ui:
        assert layout.str_content == "WordSelector"
    else:
        # Two title options
        assert layout.title() in ("SEED CHECK", "RECOVERY MODE")

    # click the number
    word_option_offset = 6
    word_options = (12, 18, 20, 24, 33)
    index = word_option_offset + word_options.index(
        num_of_words
    )  # raises if num of words is invalid
    coords = buttons.grid34(index % 3, index // 3)
    layout = debug.click(coords, wait=True)

    if legacy_ui:
        assert "Enter any share" in layout.str_content
    else:
        assert "Enter any share" in layout.text_content()


def enter_share(
    debug: "DebugLink", share: str, legacy_ui: bool = False
) -> "LayoutContent":
    layout = debug.click(buttons.OK, wait=True)

    if legacy_ui:
        assert layout.str_content == "Slip39Keyboard"
    else:
        assert "MnemonicKeyboard" in layout.str_content

    for word in share.split(" "):
        layout = enter_word(debug, word, is_slip39=True)

    return layout


def enter_shares(debug: "DebugLink", shares: list[str]) -> None:
    layout = debug.read_layout()
    expected_text = "Enter any share"
    remaining = len(shares)
    for share in shares:
        assert expected_text in layout.text_content()
        layout = enter_share(debug, share)
        remaining -= 1
        expected_text = f"{remaining} more share"

    assert "You have finished recovering your wallet" in layout.text_content()


def finalize(debug: "DebugLink") -> None:
    layout = debug.click(buttons.OK, wait=True)
    # TODO: should we also run Click/Persistence tests for model R?
    assert layout.str_content.startswith("< Homescreen ")
